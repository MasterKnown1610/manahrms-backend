from typing import Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.api.v1.models.inventory_model import InventoryItem, InventoryCategory, InventoryTransaction, TransactionType
from app.api.v1.schemas.inventory_schema import (
    InventoryItemCreate, InventoryItemUpdate,
    InventoryCategoryCreate, InventoryCategoryUpdate,
    InventoryTransactionCreate, LowStockAlert
)


def _generate_sku(db: Session, company_id: int, name: str) -> str:
    count = db.query(InventoryItem).filter(InventoryItem.company_id == company_id).count()
    prefix = "".join(c.upper() for c in name[:3] if c.isalpha()) or "ITM"
    return f"{prefix}{count + 1:06d}"


class InventoryService:

    # ── Categories ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_category(db: Session, company_id: int, data: InventoryCategoryCreate) -> InventoryCategory:
        existing = db.query(InventoryCategory).filter(
            InventoryCategory.company_id == company_id,
            InventoryCategory.name == data.name,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists")
        cat = InventoryCategory(company_id=company_id, **data.model_dump())
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

    @staticmethod
    def list_categories(db: Session, company_id: int) -> List[InventoryCategory]:
        return db.query(InventoryCategory).filter(
            InventoryCategory.company_id == company_id,
            InventoryCategory.is_active == True,
        ).order_by(InventoryCategory.name).all()

    @staticmethod
    def update_category(db: Session, company_id: int, category_id: int, data: InventoryCategoryUpdate) -> InventoryCategory:
        cat = db.query(InventoryCategory).filter(
            InventoryCategory.id == category_id,
            InventoryCategory.company_id == company_id,
        ).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(cat, field, value)
        db.commit()
        db.refresh(cat)
        return cat

    # ── Items ──────────────────────────────────────────────────────────────────

    @staticmethod
    def create_item(db: Session, company_id: int, data: InventoryItemCreate) -> InventoryItem:
        sku = data.sku or _generate_sku(db, company_id, data.name)
        existing = db.query(InventoryItem).filter(
            InventoryItem.company_id == company_id,
            InventoryItem.sku == sku,
            InventoryItem.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU '{sku}' already exists")
        item_data = data.model_dump()
        item_data["sku"] = sku
        item = InventoryItem(company_id=company_id, **item_data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_item(db: Session, company_id: int, item_id: int) -> InventoryItem:
        item = db.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.company_id == company_id,
            InventoryItem.deleted_at.is_(None),
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    @staticmethod
    def list_items(
        db: Session, company_id: int,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        low_stock_only: bool = False,
    ) -> List[InventoryItem]:
        query = db.query(InventoryItem).filter(
            InventoryItem.company_id == company_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.is_active == True,
        )
        if category_id:
            query = query.filter(InventoryItem.category_id == category_id)
        if search:
            query = query.filter(InventoryItem.name.ilike(f"%{search}%"))
        items = query.order_by(InventoryItem.name).all()
        if low_stock_only:
            items = [i for i in items if i.reorder_level is not None and i.quantity_on_hand <= i.reorder_level]
        return items

    @staticmethod
    def update_item(db: Session, company_id: int, item_id: int, data: InventoryItemUpdate) -> InventoryItem:
        item = InventoryService.get_item(db, company_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete_item(db: Session, company_id: int, item_id: int) -> None:
        from datetime import datetime
        item = InventoryService.get_item(db, company_id, item_id)
        item.deleted_at = datetime.utcnow()
        db.commit()

    # ── Transactions ───────────────────────────────────────────────────────────

    @staticmethod
    def record_transaction(
        db: Session, company_id: int, user_id: int, data: InventoryTransactionCreate
    ) -> InventoryTransaction:
        item = InventoryService.get_item(db, company_id, data.item_id)

        if data.transaction_type in (TransactionType.STOCK_OUT, TransactionType.RETURN):
            # RETURN reduces stock the same as STOCK_OUT in model (return to supplier)
            pass

        txn = InventoryTransaction(
            company_id=company_id,
            item_id=data.item_id,
            transaction_type=data.transaction_type,
            quantity=data.quantity,
            unit_price=data.unit_price,
            reference_id=data.reference_id,
            reference_type=data.reference_type,
            notes=data.notes,
            performed_by_user_id=user_id,
        )

        if data.transaction_type == TransactionType.STOCK_IN:
            item.quantity_on_hand += data.quantity
        elif data.transaction_type in (TransactionType.STOCK_OUT, TransactionType.RETURN):
            if item.quantity_on_hand < data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock. Available: {item.quantity_on_hand} {item.unit or ''}"
                )
            item.quantity_on_hand -= data.quantity
        elif data.transaction_type == TransactionType.ADJUSTMENT:
            item.quantity_on_hand = data.quantity

        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def get_low_stock_alerts(db: Session, company_id: int) -> List[LowStockAlert]:
        items = db.query(InventoryItem).filter(
            InventoryItem.company_id == company_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.is_active == True,
            InventoryItem.reorder_level.isnot(None),
        ).all()
        return [
            LowStockAlert(
                item_id=i.id,
                name=i.name,
                sku=i.sku,
                quantity_on_hand=i.quantity_on_hand,
                reorder_level=i.reorder_level,
                unit=i.unit,
            )
            for i in items
            if i.quantity_on_hand <= i.reorder_level
        ]
