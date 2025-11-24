"""
Schemas for Leave Management
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# Leave Type Schemas
class LeaveTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Leave type name")
    code: str = Field(..., min_length=1, max_length=50, description="Leave type code (e.g., SL, CL)")
    description: Optional[str] = Field(None, description="Leave type description")
    max_days_per_year: Optional[int] = Field(None, ge=0, description="Maximum days allowed per year")
    is_paid: bool = Field(True, description="Is this a paid leave")
    requires_approval: bool = Field(True, description="Requires manager approval")
    can_carry_forward: bool = Field(False, description="Can carry forward unused leaves")


class LeaveTypeCreate(LeaveTypeBase):
    pass


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    max_days_per_year: Optional[int] = Field(None, ge=0)
    is_paid: Optional[bool] = None
    requires_approval: Optional[bool] = None
    can_carry_forward: Optional[bool] = None
    is_active: Optional[bool] = None


class LeaveTypeResponse(LeaveTypeBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Leave Request Schemas
class LeaveRequestBase(BaseModel):
    leave_type_id: int = Field(..., description="Leave type ID")
    start_date: date = Field(..., description="Leave start date")
    end_date: date = Field(..., description="Leave end date")
    reason: Optional[str] = Field(None, description="Reason for leave")


class LeaveRequestCreate(LeaveRequestBase):
    pass


class LeaveRequestResponse(LeaveRequestBase):
    id: int
    company_id: int
    employee_id: int
    number_of_days: int
    status: str
    applied_date: datetime
    approved_by_user_id: Optional[int] = None
    approved_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Related data
    employee_name: Optional[str] = None
    leave_type_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    approved_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class LeaveRequestApproval(BaseModel):
    status: str = Field(..., description="Approval status: 'approved' or 'rejected'")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (if rejected)")


# Leave Balance Schemas
class LeaveBalanceResponse(BaseModel):
    id: int
    company_id: int
    employee_id: int
    leave_type_id: int
    year: int
    total_days: Decimal
    used_days: Decimal
    pending_days: Decimal
    available_days: Decimal
    carried_forward_days: Decimal
    
    # Related data
    leave_type_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    employee_name: Optional[str] = None

    class Config:
        from_attributes = True


# Leave Summary Schemas
class LeaveSummaryResponse(BaseModel):
    """Summary of all leave balances for an employee"""
    employee_id: int
    employee_name: str
    year: int
    leave_balances: List[LeaveBalanceResponse]
    total_available_days: Decimal
    total_used_days: Decimal
    total_pending_days: Decimal


# Leave Calendar Schemas
class LeaveCalendarEntry(BaseModel):
    """Entry for leave calendar"""
    date: date
    employee_id: int
    employee_name: str
    leave_type: str
    leave_type_code: str
    status: str
    number_of_days: int


class LeaveCalendarResponse(BaseModel):
    """Leave calendar for a date range"""
    start_date: date
    end_date: date
    leaves: List[LeaveCalendarEntry]


# Statistics Schemas
class LeaveStatisticsResponse(BaseModel):
    """Leave statistics for a company"""
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    total_leave_days: int
    average_leave_days: float

