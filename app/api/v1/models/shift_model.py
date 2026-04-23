"""
Shift Scheduling Models — define shift patterns and assign employees.
Critical for hospitals (3 shifts/day) and restaurants (morning/evening shifts).
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Boolean, Text, Time, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_shift_company_name"),
        Index("idx_shift_company", "company_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)   # "Morning Shift", "Night Shift"
    description = Column(Text, nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    # shift_days: ["monday","tuesday","wednesday","thursday","friday"] or ["all"]
    shift_days = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = relationship("ShiftAssignment", back_populates="shift")


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_id", "shift_id", "effective_from",
                         name="uq_shift_assign_emp_shift_date"),
        Index("idx_shift_assign_company", "company_id"),
        Index("idx_shift_assign_employee", "employee_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)     # null = current/ongoing
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shift = relationship("Shift", back_populates="assignments")
    employee = relationship("Employee")
    assigned_by = relationship("User")
