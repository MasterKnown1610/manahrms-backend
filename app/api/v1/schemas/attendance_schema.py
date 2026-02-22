from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time


class AttendanceBase(BaseModel):
    attendance_date: date
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None


class AttendanceCreate(BaseModel):
    """Schema for creating attendance (punch in)"""
    pass  # Date and time will be set automatically


class AttendanceUpdate(BaseModel):
    """Schema for updating attendance (punch out)"""
    pass  # Punch out time will be set automatically


class EmployeeInfo(BaseModel):
    """Schema for employee information in attendance response"""
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    
    model_config = {"from_attributes": True}


class AttendanceResponse(BaseModel):
    """Schema for attendance response"""
    id: int
    company_id: int
    employee_id: int
    attendance_date: date
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None
    work_duration_hours: Optional[int] = None  # Duration in minutes
    is_present: bool
    is_checked_out: bool
    employee: Optional[EmployeeInfo] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AttendanceCalendarDay(BaseModel):
    """Schema for a single day in calendar view"""
    date: date
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None
    work_duration_minutes: Optional[int] = None
    is_present: bool
    is_checked_out: bool


class AttendanceCalendarResponse(BaseModel):
    """Schema for calendar view response"""
    employee_id: int
    month: int
    year: int
    days: List[AttendanceCalendarDay]
    total_present_days: int
    total_work_hours: float  # Total hours worked in the month


class AttendanceStatsResponse(BaseModel):
    """Schema for attendance statistics"""
    total_employees: int
    present_today: int
    absent_today: int
    checked_in_but_not_out: int


class AttendanceListResponse(BaseModel):
    """Schema for listing attendance records"""
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    attendance_date: date
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None
    work_duration_minutes: Optional[int] = None
    is_present: bool
    is_checked_out: bool


class PunchInResponse(BaseModel):
    """Schema for punch in response"""
    success: bool
    message: str
    attendance: AttendanceResponse


class PunchOutResponse(BaseModel):
    """Schema for punch out response"""
    success: bool
    message: str
    attendance: AttendanceResponse
    work_duration_minutes: Optional[int] = None


class EmployeePresentInfo(BaseModel):
    """Schema for employee present information"""
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    position: Optional[str] = None
    department_id: Optional[int] = None
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None
    work_duration_minutes: Optional[int] = None
    is_checked_out: bool


class EmployeesPresentResponse(BaseModel):
    """Schema for list of employees present on a date"""
    date: date
    total_present: int
    members: List[EmployeePresentInfo]
