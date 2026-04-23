"""
Donation Models — for temples, religious organizations, and charitable events.
Tracks donor info, purpose, amount, and payment mode.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Text, Numeric, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class DonationMode(str, enum.Enum):
    CASH = "cash"
    ONLINE = "online"
    CHEQUE = "cheque"
    DD = "demand_draft"
    UPI = "upi"


class Donation(Base):
    __tablename__ = "donations"
    __table_args__ = (
        UniqueConstraint("company_id", "receipt_number", name="uq_donation_company_receipt"),
        Index("idx_donation_company", "company_id"),
        Index("idx_donation_company_date", "company_id", "donated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    donor_name = Column(String(200), nullable=False)
    donor_phone = Column(String(20), nullable=True)
    donor_email = Column(String(254), nullable=True)
    donor_address = Column(Text, nullable=True)
    purpose = Column(String(300), nullable=True)        # "Temple Construction", "Annadanam", "Event"
    amount = Column(Numeric(14, 2), nullable=False)
    donation_mode = Column(Enum(DonationMode), nullable=False, default=DonationMode.CASH)
    receipt_number = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    donated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    razorpay_order_id = Column(String(255), nullable=True, index=True)
    razorpay_payment_id = Column(String(255), nullable=True, index=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    received_by = relationship("User")
