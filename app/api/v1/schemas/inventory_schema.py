from typing import Optional, Any, Dict, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.api.v1.models.inventory_model import ItemType, TransactionType


# ── Category ─────────────────────────────────────────────────────────────────

class InventoryCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    parent_category_id: Optional[int] = None


class InventoryCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class InventoryCategoryResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: Optional[str] = None
    parent_category_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Item ─────────────────────────────────────────────────────────────────────

class InventoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sku: Optional[str] = None
    category_id: Optional[int] = None
    item_type: ItemType = ItemType.CONSUMABLE
    unit: Optional[str] = None
    quantity_on_hand: Decimal = Field(default=Decimal("0"))
    reorder_level: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    item_type: Optional[ItemType] = None
    unit: Optional[str] = None
    reorder_level: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class InventoryItemResponse(BaseModel):
    id: int
    company_id: int
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    sku: Optional[str] = None
    item_type: ItemType
    unit: Optional[str] = None
    quantity_on_hand: Decimal
    reorder_level: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


# ── Transaction ───────────────────────────────────────────────────────────────

class InventoryTransactionCreate(BaseModel):
    item_id: int
    transaction_type: TransactionType
    quantity: Decimal = Field(..., gt=0)
    unit_price: Optional[Decimal] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    notes: Optional[str] = None


class InventoryTransactionResponse(BaseModel):
    id: int
    company_id: int
    item_id: int
    transaction_type: TransactionType
    quantity: Decimal
    unit_price: Optional[Decimal] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    notes: Optional[str] = None
    performed_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LowStockAlert(BaseModel):
    item_id: int
    name: str
    sku: Optional[str] = None
    quantity_on_hand: Decimal
    reorder_level: Decimal
    unit: Optional[str] = None

    model_config = {"from_attributes": True}
