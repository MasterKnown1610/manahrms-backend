from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr
from app.api.v1.models.donation_model import DonationMode


class DonationCreate(BaseModel):
    donor_name: str = Field(..., min_length=1, max_length=200)
    donor_phone: Optional[str] = None
    donor_email: Optional[EmailStr] = None
    donor_address: Optional[str] = None
    purpose: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    donation_mode: DonationMode = DonationMode.CASH
    notes: Optional[str] = None
    donated_at: Optional[datetime] = None


class DonationUpdate(BaseModel):
    donor_name: Optional[str] = Field(None, min_length=1, max_length=200)
    donor_phone: Optional[str] = None
    donor_email: Optional[EmailStr] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None


class DonationResponse(BaseModel):
    id: int
    company_id: int
    donor_name: str
    donor_phone: Optional[str] = None
    donor_email: Optional[str] = None
    donor_address: Optional[str] = None
    purpose: Optional[str] = None
    amount: Decimal
    donation_mode: DonationMode
    receipt_number: str
    notes: Optional[str] = None
    donated_at: datetime
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    received_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
