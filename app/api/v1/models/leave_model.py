"""
Leave Management Models
Handles employee leave requests, approvals, and balances
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, Boolean, Enum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

from app.db.base import Base


class LeaveStatus(str, enum.Enum):
    """Leave request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveType(Base):
    """
    Leave types available in the system (Sick, Casual, Annual, etc.)
    Each company can have different leave types
    """
    __tablename__ = "leave_types"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)  # e.g., "Sick Leave", "Casual Leave"
    code = Column(String(50), nullable=False)  # e.g., "SL", "CL", "AL"
    description = Column(Text, nullable=True)
    
    # Leave policy
    max_days_per_year = Column(Integer, nullable=True)  # Maximum days allowed per year
    is_paid = Column(Boolean, default=True)  # Is this a paid leave
    requires_approval = Column(Boolean, default=True)  # Requires manager approval
    can_carry_forward = Column(Boolean, default=False)  # Can carry forward unused leaves
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="leave_types")
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")
    
    def __repr__(self):
        return f"<LeaveType {self.code} - {self.name}>"


class LeaveRequest(Base):
    """
    Employee leave requests
    """
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id", ondelete="SET NULL"), nullable=False, index=True)
    
    # Leave details
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    number_of_days = Column(Integer, nullable=False)  # Calculated days
    reason = Column(Text, nullable=True)  # Reason for leave
    
    # Status and approval
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False, index=True)
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Approver information
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    employee = relationship("Employee", back_populates="leave_requests")
    leave_type = relationship("LeaveType", back_populates="leave_requests")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    
    def __repr__(self):
        return f"<LeaveRequest {self.id} - {self.employee_id} ({self.status.value})>"


class LeaveBalance(Base):
    """
    Employee leave balances for each leave type
    Tracks available, used, and pending leaves
    """
    __tablename__ = "leave_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Balance tracking
    year = Column(Integer, nullable=False, index=True)  # Year for this balance (e.g., 2024)
    total_days = Column(Numeric(5, 2), nullable=False, default=0)  # Total allocated days
    used_days = Column(Numeric(5, 2), nullable=False, default=0)  # Days used (approved)
    pending_days = Column(Numeric(5, 2), nullable=False, default=0)  # Days pending approval
    available_days = Column(Numeric(5, 2), nullable=False, default=0)  # Available days (total - used - pending)
    
    # Carry forward
    carried_forward_days = Column(Numeric(5, 2), nullable=False, default=0)  # Days carried from previous year
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    employee = relationship("Employee", back_populates="leave_balances")
    leave_type = relationship("LeaveType")
    
    # Unique constraint: one balance per employee, leave type, and year
    __table_args__ = (
        {"comment": "Unique constraint on (employee_id, leave_type_id, year) should be added via migration"}
    )
    
    def __repr__(self):
        return f"<LeaveBalance {self.employee_id} - {self.leave_type_id} ({self.year}): {self.available_days} days>"

