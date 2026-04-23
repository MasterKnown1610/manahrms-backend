from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.inventory_schema import (
    InventoryCategoryCreate, InventoryCategoryUpdate, InventoryCategoryResponse,
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
    InventoryTransactionCreate, InventoryTransactionResponse,
    LowStockAlert,
)
from app.api.v1.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[InventoryCategoryResponse])
async def list_categories(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return InventoryService.list_categories(db, current_user.company_id)


@router.post("/categories", response_model=InventoryCategoryResponse, status_code=201)
async def create_category(
    data: InventoryCategoryCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return InventoryService.create_category(db, current_user.company_id, data)


@router.patch("/categories/{category_id}", response_model=InventoryCategoryResponse)
async def update_category(
    category_id: int,
    data: InventoryCategoryUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return InventoryService.update_category(db, current_user.company_id, category_id, data)


# ── Items ─────────────────────────────────────────────────────────────────────

@router.get("/items", response_model=List[InventoryItemResponse])
async def list_items(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    items = InventoryService.list_items(db, current_user.company_id, category_id, search, low_stock_only)
    result = []
    for item in items:
        r = InventoryItemResponse.model_validate(item)
        r.is_low_stock = bool(item.reorder_level is not None and item.quantity_on_hand <= item.reorder_level)
        result.append(r)
    return result


@router.post("/items", response_model=InventoryItemResponse, status_code=201)
async def create_item(
    data: InventoryItemCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return InventoryService.create_item(db, current_user.company_id, data)


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_item(
    item_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return InventoryService.get_item(db, current_user.company_id, item_id)


@router.patch("/items/{item_id}", response_model=InventoryItemResponse)
async def update_item(
    item_id: int,
    data: InventoryItemUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return InventoryService.update_item(db, current_user.company_id, item_id, data)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    InventoryService.delete_item(db, current_user.company_id, item_id)


# ── Transactions ──────────────────────────────────────────────────────────────

@router.post("/transactions", response_model=InventoryTransactionResponse, status_code=201)
async def record_transaction(
    data: InventoryTransactionCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return InventoryService.record_transaction(db, current_user.company_id, current_user.id, data)


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts/low-stock", response_model=List[LowStockAlert])
async def get_low_stock_alerts(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return InventoryService.get_low_stock_alerts(db, current_user.company_id)
