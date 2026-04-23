"""
Booking & Scheduling Models.
Hospital: doctor appointments | Restaurant: table reservations | Event: venue bookings
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Boolean, Text, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class BookingResource(Base):
    __tablename__ = "booking_resources"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_booking_resource_company_name"),
        Index("idx_booking_resource_company", "company_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    # resource_type: "room", "table", "doctor_slot", "venue", "vehicle", "equipment"
    resource_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    custom_attributes = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = relationship("Booking", back_populates="resource")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("idx_booking_company", "company_id"),
        Index("idx_booking_company_status", "company_id", "status"),
        Index("idx_booking_company_start", "company_id", "start_datetime"),
        Index("idx_booking_resource", "resource_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("booking_resources.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("crm_clients.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    notes = Column(Text, nullable=True)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    booked_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancelled_reason = Column(Text, nullable=True)
    custom_attributes = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resource = relationship("BookingResource", back_populates="bookings")
    client = relationship("Client")
    employee = relationship("Employee")
    booked_by = relationship("User")
