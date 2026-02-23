"""
Calendar API Routes
Unified calendar view for meetings and events
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
import logging

from app.db.session import get_database_session
from app.api.v1.schemas.event_schema import (
    CalendarDayUnifiedResponse,
    CalendarMonthUnifiedResponse,
    CalendarMonthDayResponse,
    CalendarEventItem
)
from app.api.v1.services.calendar_service import CalendarService
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.models.employee_model import Employee

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/day", response_model=CalendarDayUnifiedResponse)
async def get_calendar_day(
    date: date = Query(..., description="Date to get calendar items for (YYYY-MM-DD)"),
    timezone: str = Query(..., description="User's timezone (e.g., Asia/Kolkata)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get unified calendar day view with both meetings and events.
    
    Returns:
    - Meetings where the user is a participant
    - Events visible to the user based on visibility rules (ALL, DEPARTMENT, SELECTED_USERS)
    
    All times are converted to the user's specified timezone.
    """
    logger.info(f"Getting calendar for date {date} in timezone {timezone} for user {current_user.id}")
    
    # Get user's department ID for event visibility check
    user_department_id = None
    if current_user.employee_id:
        employee = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
        if employee:
            user_department_id = employee.department_id
    
    # Get unified calendar data (meetings + events)
    calendar_data = CalendarService.get_unified_calendar_day(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        user_department_id=user_department_id,
        target_date=date,
        user_timezone=timezone
    )
    
    return CalendarDayUnifiedResponse(
        date=date.isoformat(),
        timezone=timezone,
        meetings=[
            CalendarEventItem(**meeting) for meeting in calendar_data["meetings"]
        ],
        events=[
            CalendarEventItem(**event) for event in calendar_data["events"]
        ]
    )


@router.get("/month", response_model=CalendarMonthUnifiedResponse)
async def get_calendar_month(
    year: int = Query(..., ge=2000, le=2100, description="Year (e.g., 2026)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    timezone: str = Query(..., description="User's timezone (e.g., Asia/Kolkata)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get unified calendar month view with both meetings and events.
    
    Returns all days in the specified month with:
    - Meetings where the user is a participant
    - Events visible to the user based on visibility rules (ALL, DEPARTMENT, SELECTED_USERS)
    
    All times are converted to the user's specified timezone.
    Days without any meetings or events are still included with empty lists.
    """
    logger.info(f"Getting calendar for month {year}-{month} in timezone {timezone} for user {current_user.id}")
    
    # Get user's department ID for event visibility check
    user_department_id = None
    if current_user.employee_id:
        employee = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
        if employee:
            user_department_id = employee.department_id
    
    # Get unified calendar data for the month
    calendar_data = CalendarService.get_unified_calendar_month(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        user_department_id=user_department_id,
        year=year,
        month=month,
        user_timezone=timezone
    )
    
    # Get all days in the month (including days without events/meetings)
    from calendar import monthrange
    from datetime import datetime
    
    _, last_day = monthrange(year, month)
    all_days = []
    
    for day in range(1, last_day + 1):
        date_obj = date(year, month, day)
        date_str = date_obj.isoformat()
        
        # Get meetings and events for this day
        meetings = calendar_data.get(date_str, {}).get("meetings", [])
        events = calendar_data.get(date_str, {}).get("events", [])
        
        all_days.append(
            CalendarMonthDayResponse(
                date=date_str,
                meetings=[CalendarEventItem(**meeting) for meeting in meetings],
                events=[CalendarEventItem(**event) for event in events]
            )
        )
    
    return CalendarMonthUnifiedResponse(
        year=year,
        month=month,
        timezone=timezone,
        days=all_days
    )

