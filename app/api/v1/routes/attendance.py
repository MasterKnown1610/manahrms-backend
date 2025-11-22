from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, timedelta

from app.db.session import get_database_session
from app.api.v1.dependencies import (
    get_current_authenticated_user,
    require_admin_role,
    require_employee_role
)
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.attendance_model import Attendance
from app.api.v1.services.attendance_service import AttendanceService
from app.api.v1.schemas.attendance_schema import (
    AttendanceResponse,
    AttendanceCalendarResponse,
    AttendanceCalendarDay,
    AttendanceStatsResponse,
    AttendanceListResponse,
    PunchInResponse,
    PunchOutResponse
)
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.utils.pagination import paginate_query, create_paginated_response


router = APIRouter(prefix="/attendance", tags=["Attendance"])


def get_employee_id_from_user(current_user: User, db: Session) -> int:
    """Get employee_id from current user"""
    if current_user.role == UserRole.EMPLOYEE:
        if not current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "Employee record not linked to user account",
                    "error_code": "EMPLOYEE_NOT_LINKED"
                }
            )
        return current_user.employee_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Only employees can perform this action",
                "error_code": "EMPLOYEE_ACCESS_REQUIRED"
            }
        )


@router.post("/punch-in", response_model=PunchInResponse, status_code=status.HTTP_200_OK)
async def punch_in(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Employee punch in endpoint.
    Records the current time as punch in time for today.
    """
    employee_id = get_employee_id_from_user(current_user, db)
    
    attendance = AttendanceService.punch_in(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id
    )
    
    return PunchInResponse(
        success=True,
        message=f"Punched in successfully at {attendance.punch_in_time.strftime('%H:%M:%S')}",
        attendance=AttendanceResponse.model_validate(attendance)
    )


@router.post("/punch-out", response_model=PunchOutResponse, status_code=status.HTTP_200_OK)
async def punch_out(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Employee punch out endpoint.
    Records the current time as punch out time for today.
    """
    employee_id = get_employee_id_from_user(current_user, db)
    
    attendance = AttendanceService.punch_out(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id
    )
    
    work_duration = attendance.calculate_work_duration()
    
    return PunchOutResponse(
        success=True,
        message=f"Punched out successfully at {attendance.punch_out_time.strftime('%H:%M:%S')}",
        attendance=AttendanceResponse.model_validate(attendance),
        work_duration_minutes=work_duration
    )


@router.get("/today", response_model=Optional[AttendanceResponse])
async def get_today_attendance(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get today's attendance record for the current employee.
    """
    employee_id = get_employee_id_from_user(current_user, db)
    
    attendance = AttendanceService.get_today_attendance(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id
    )
    
    if not attendance:
        return None
    
    return AttendanceResponse.model_validate(attendance)


@router.get("/calendar", response_model=AttendanceCalendarResponse)
async def get_attendance_calendar(
    year: int = Query(..., ge=2000, le=2100, description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get attendance calendar for a specific month.
    Shows all days with punch in/out times for the current employee.
    """
    employee_id = get_employee_id_from_user(current_user, db)
    
    attendances, present_days, total_hours = AttendanceService.get_attendance_calendar(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id,
        year=year,
        month=month
    )
    
    # Create a dictionary for quick lookup
    attendance_dict = {a.attendance_date: a for a in attendances}
    
    # Get all days in the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    days = []
    current_date = start_date
    while current_date < end_date:
        attendance = attendance_dict.get(current_date)
        if attendance:
            days.append(AttendanceCalendarDay(
                date=current_date,
                punch_in_time=attendance.punch_in_time,
                punch_out_time=attendance.punch_out_time,
                work_duration_minutes=attendance.work_duration_hours,
                is_present=attendance.is_present,
                is_checked_out=attendance.is_checked_out
            ))
        else:
            days.append(AttendanceCalendarDay(
                date=current_date,
                punch_in_time=None,
                punch_out_time=None,
                work_duration_minutes=None,
                is_present=False,
                is_checked_out=False
            ))
        # Move to next day
        current_date += timedelta(days=1)
    
    return AttendanceCalendarResponse(
        employee_id=employee_id,
        month=month,
        year=year,
        days=days,
        total_present_days=present_days,
        total_work_hours=round(total_hours, 2)
    )


@router.get("/stats", response_model=AttendanceStatsResponse)
async def get_attendance_stats(
    target_date: Optional[date] = Query(None, description="Date to get stats for (default: today)"),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Get attendance statistics for a specific date.
    Admin only endpoint.
    Shows how many employees are present, absent, etc.
    """
    stats = AttendanceService.get_attendance_stats(
        db=db,
        company_id=current_user.company_id,
        target_date=target_date
    )
    
    return AttendanceStatsResponse(**stats)


@router.post("/query", response_model=PaginatedResponse[AttendanceListResponse])
async def query_attendance_records(
    pagination_request: PaginationRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Query attendance records with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    Admin only endpoint.
    """
    # Build base query - join with Employee to filter by company
    query = db.query(Attendance).join(
        Employee,
        Attendance.employee_id == Employee.id
    ).filter(
        Employee.company_id == current_user.company_id
    )
    
    # Apply pagination, filters, and sorting
    attendances, pagination_info = paginate_query(query, pagination_request, Attendance)
    
    # Build response with employee names
    items = []
    for att in attendances:
        employee = db.query(Employee).filter(Employee.id == att.employee_id).first()
        items.append(AttendanceListResponse(
            employee_id=att.employee_id,
            employee_name=employee.full_name if employee else "Unknown",
            attendance_date=att.attendance_date,
            punch_in_time=att.punch_in_time,
            punch_out_time=att.punch_out_time,
            work_duration_minutes=att.work_duration_hours,
            is_present=att.is_present,
            is_checked_out=att.is_checked_out
        ))
    
    return PaginatedResponse[AttendanceListResponse](
        data=items,
        pagination=pagination_info
    )


@router.get("/employee/{employee_id}/calendar", response_model=AttendanceCalendarResponse)
async def get_employee_attendance_calendar(
    employee_id: int,
    year: int = Query(..., ge=2000, le=2100, description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Get attendance calendar for a specific employee (admin only).
    """
    # Verify employee belongs to company
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Employee not found",
                "error_code": "EMPLOYEE_NOT_FOUND"
            }
        )
    
    attendances, present_days, total_hours = AttendanceService.get_attendance_calendar(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id,
        year=year,
        month=month
    )
    
    # Create calendar days
    attendance_dict = {a.attendance_date: a for a in attendances}
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    days = []
    current_date = start_date
    while current_date < end_date:
        attendance = attendance_dict.get(current_date)
        if attendance:
            days.append(AttendanceCalendarDay(
                date=current_date,
                punch_in_time=attendance.punch_in_time,
                punch_out_time=attendance.punch_out_time,
                work_duration_minutes=attendance.work_duration_hours,
                is_present=attendance.is_present,
                is_checked_out=attendance.is_checked_out
            ))
        else:
            days.append(AttendanceCalendarDay(
                date=current_date,
                punch_in_time=None,
                punch_out_time=None,
                work_duration_minutes=None,
                is_present=False,
                is_checked_out=False
            ))
        current_date += timedelta(days=1)
    
    return AttendanceCalendarResponse(
        employee_id=employee_id,
        month=month,
        year=year,
        days=days,
        total_present_days=present_days,
        total_work_hours=round(total_hours, 2)
    )

