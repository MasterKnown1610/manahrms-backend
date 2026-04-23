from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from app.api.v1.models.billing_ops_model import InvoiceStatus


class InvoiceItemCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    total_price: Optional[Decimal] = None


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    client_id: Optional[int] = None
    title: Optional[str] = None
    issue_date: date
    due_date: Optional[date] = None
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    items: List[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    title: Optional[str] = None
    due_date: Optional[date] = None
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[InvoiceStatus] = None
    payment_method: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    company_id: int
    invoice_number: str
    client_id: Optional[int] = None
    title: Optional[str] = None
    status: InvoiceStatus
    issue_date: date
    due_date: Optional[date] = None
    subtotal: Decimal
    tax_percent: Optional[Decimal] = None
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    razorpay_order_id: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItemResponse] = []

    model_config = {"from_attributes": True}
