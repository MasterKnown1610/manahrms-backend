"""
Inventory Models — universal for all industries.
Hospital: medicines | Restaurant: ingredients | Temple: prasad/flowers | School: supplies
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Boolean, Text, Numeric, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ItemType(str, enum.Enum):
    CONSUMABLE = "consumable"
    ASSET = "asset"
    SERVICE = "service"


class TransactionType(str, enum.Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ADJUSTMENT = "adjustment"
    RETURN = "return"


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_inv_category_company_name"),
        Index("idx_inv_category_company", "company_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    parent_category_id = Column(Integer, ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("InventoryItem", back_populates="category")
    subcategories = relationship("InventoryCategory", backref="parent", remote_side=[id])


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_inv_item_company_sku"),
        Index("idx_inv_item_company", "company_id"),
        Index("idx_inv_item_company_type", "company_id", "item_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(100), nullable=True)         # auto-generated if not provided
    item_type = Column(Enum(ItemType), nullable=False, default=ItemType.CONSUMABLE)
    unit = Column(String(50), nullable=True)          # kg, pieces, liters, tablets, etc.
    quantity_on_hand = Column(Numeric(12, 3), nullable=False, default=0)
    reorder_level = Column(Numeric(12, 3), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=True)
    supplier_name = Column(String(200), nullable=True)
    supplier_contact = Column(String(100), nullable=True)
    custom_attributes = Column(JSONB, nullable=True)  # industry-specific extra fields
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("InventoryCategory", back_populates="items")
    transactions = relationship("InventoryTransaction", back_populates="item")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("idx_inv_txn_company_item", "company_id", "item_id"),
        Index("idx_inv_txn_company_created", "company_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=True)
    reference_id = Column(Integer, nullable=True)     # task_id, booking_id, etc.
    reference_type = Column(String(50), nullable=True) # "task", "booking", "manual"
    notes = Column(Text, nullable=True)
    performed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    item = relationship("InventoryItem", back_populates="transactions")
    performed_by = relationship("User")
