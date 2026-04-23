"""
Billing Operations Models — invoices and payments (separate from subscription billing).
For generating client invoices, quotations, and tracking operational payments.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Boolean, Text, Numeric, Date, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_invoice_company_number"),
        Index("idx_invoice_company", "company_id"),
        Index("idx_invoice_company_status", "company_id", "status"),
        Index("idx_invoice_client", "client_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(100), nullable=False)
    client_id = Column(Integer, ForeignKey("crm_clients.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=True)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    tax_percent = Column(Numeric(5, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(14, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(14, 2), nullable=False, default=0)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    payment_method = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    razorpay_order_id = Column(String(255), nullable=True, index=True)
    razorpay_payment_id = Column(String(255), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client")
    created_by = relationship("User")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("idx_invoice_item_invoice", "invoice_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(14, 2), nullable=False, default=0)
    total_price = Column(Numeric(14, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="items")
