"""
Leave Management Routes
Handles employee leave requests, approvals, and balances
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import date, timedelta

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.models.employee_model import Employee
from app.api.v1.schemas.leave_schema import (
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveRequestApproval,
    LeaveBalanceResponse,
    LeaveSummaryResponse,
    LeaveCalendarResponse,
    LeaveCalendarEntry,
    LeaveTypeCreate,
    LeaveTypeResponse,
    LeaveTypeUpdate
)
from app.api.v1.services.leave_service import LeaveService
from app.api.v1.models.leave_model import LeaveRequest, LeaveStatus
from app.api.v1.utils.error_handler import raise_http_exception


router = APIRouter(prefix="/leaves", tags=["Leave Management"])


# Leave Request Endpoints
@router.post("/apply", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_leave(
    request: LeaveRequestCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Apply for leave.
    
    Employees can apply for leave by providing:
    - Leave type
    - Start and end dates
    - Reason (optional)
    """
    # Get employee ID from user
    if not current_user.employee_id:
        raise_http_exception(
            message="User is not associated with an employee",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="NO_EMPLOYEE_ASSOCIATION"
        )
    
    leave_service = LeaveService()
    leave_request = leave_service.apply_for_leave(
        db=db,
        company_id=current_user.company_id,
        employee_id=current_user.employee_id,
        leave_type_id=request.leave_type_id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason
    )
    
    # Load relationships for response
    db.refresh(leave_request)
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request.id).first()
    
    response = LeaveRequestResponse(
        id=leave_request.id,
        company_id=leave_request.company_id,
        employee_id=leave_request.employee_id,
        leave_type_id=leave_request.leave_type_id,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        number_of_days=leave_request.number_of_days,
        reason=leave_request.reason,
        status=leave_request.status.value,
        applied_date=leave_request.applied_date,
        approved_by_user_id=leave_request.approved_by_user_id,
        approved_date=leave_request.approved_date,
        rejection_reason=leave_request.rejection_reason,
        created_at=leave_request.created_at,
        updated_at=leave_request.updated_at,
        employee_name=leave_request.employee.full_name if leave_request.employee else None,
        leave_type_name=leave_request.leave_type.name if leave_request.leave_type else None,
        leave_type_code=leave_request.leave_type.code if leave_request.leave_type else None,
        approved_by_name=leave_request.approved_by.full_name if leave_request.approved_by else None
    )
    
    return response


@router.get("/requests", response_model=List[LeaveRequestResponse], status_code=status.HTTP_200_OK)
async def get_leave_requests(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get leave requests.
    
    - Employees can see their own requests
    - Admins can see all requests in their company
    """
    leave_service = LeaveService()
    
    # If employee, only show their own requests
    if current_user.role.value == "employee" and current_user.employee_id:
        employee_id = current_user.employee_id
    
    leave_requests = leave_service.get_leave_requests(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date
    )
    
    # Format response
    response = []
    for lr in leave_requests:
        response.append(LeaveRequestResponse(
            id=lr.id,
            company_id=lr.company_id,
            employee_id=lr.employee_id,
            leave_type_id=lr.leave_type_id,
            start_date=lr.start_date,
            end_date=lr.end_date,
            number_of_days=lr.number_of_days,
            reason=lr.reason,
            status=lr.status.value,
            applied_date=lr.applied_date,
            approved_by_user_id=lr.approved_by_user_id,
            approved_date=lr.approved_date,
            rejection_reason=lr.rejection_reason,
            created_at=lr.created_at,
            updated_at=lr.updated_at,
            employee_name=lr.employee.full_name if lr.employee else None,
            leave_type_name=lr.leave_type.name if lr.leave_type else None,
            leave_type_code=lr.leave_type.code if lr.leave_type else None,
            approved_by_name=lr.approved_by.full_name if lr.approved_by else None
        ))
    
    return response


@router.post("/requests/{leave_request_id}/approve", response_model=LeaveRequestResponse, status_code=status.HTTP_200_OK)
async def approve_leave_request(
    leave_request_id: int,
    approval: LeaveRequestApproval,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Approve or reject a leave request.
    
    Only admins can approve/reject leave requests.
    """
    if current_user.role.value != "admin":
        raise_http_exception(
            message="Only admins can approve leave requests",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED"
        )
    
    leave_service = LeaveService()
    leave_request = leave_service.approve_leave(
        db=db,
        leave_request_id=leave_request_id,
        approver_user_id=current_user.id,
        approved=approval.status == "approved",
        rejection_reason=approval.rejection_reason
    )
    
    # Refresh to get updated data
    db.refresh(leave_request)
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request.id).first()
    
    return LeaveRequestResponse(
        id=leave_request.id,
        company_id=leave_request.company_id,
        employee_id=leave_request.employee_id,
        leave_type_id=leave_request.leave_type_id,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        number_of_days=leave_request.number_of_days,
        reason=leave_request.reason,
        status=leave_request.status.value,
        applied_date=leave_request.applied_date,
        approved_by_user_id=leave_request.approved_by_user_id,
        approved_date=leave_request.approved_date,
        rejection_reason=leave_request.rejection_reason,
        created_at=leave_request.created_at,
        updated_at=leave_request.updated_at,
        employee_name=leave_request.employee.full_name if leave_request.employee else None,
        leave_type_name=leave_request.leave_type.name if leave_request.leave_type else None,
        leave_type_code=leave_request.leave_type.code if leave_request.leave_type else None,
        approved_by_name=leave_request.approved_by.full_name if leave_request.approved_by else None
    )


@router.post("/requests/{leave_request_id}/cancel", response_model=LeaveRequestResponse, status_code=status.HTTP_200_OK)
async def cancel_leave_request(
    leave_request_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Cancel a pending leave request.
    
    Employees can only cancel their own pending leave requests.
    """
    if not current_user.employee_id:
        raise_http_exception(
            message="User is not associated with an employee",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="NO_EMPLOYEE_ASSOCIATION"
        )
    
    leave_service = LeaveService()
    leave_request = leave_service.cancel_leave_request(
        db=db,
        leave_request_id=leave_request_id,
        employee_id=current_user.employee_id
    )
    
    db.refresh(leave_request)
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request.id).first()
    
    return LeaveRequestResponse(
        id=leave_request.id,
        company_id=leave_request.company_id,
        employee_id=leave_request.employee_id,
        leave_type_id=leave_request.leave_type_id,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        number_of_days=leave_request.number_of_days,
        reason=leave_request.reason,
        status=leave_request.status.value,
        applied_date=leave_request.applied_date,
        approved_by_user_id=leave_request.approved_by_user_id,
        approved_date=leave_request.approved_date,
        rejection_reason=leave_request.rejection_reason,
        created_at=leave_request.created_at,
        updated_at=leave_request.updated_at,
        employee_name=leave_request.employee.full_name if leave_request.employee else None,
        leave_type_name=leave_request.leave_type.name if leave_request.leave_type else None,
        leave_type_code=leave_request.leave_type.code if leave_request.leave_type else None,
        approved_by_name=leave_request.approved_by.full_name if leave_request.approved_by else None
    )


# Leave Balance Endpoints
@router.get("/balance", response_model=LeaveSummaryResponse, status_code=status.HTTP_200_OK)
async def get_leave_balance(
    employee_id: Optional[int] = Query(None, description="Employee ID (admin only)"),
    year: Optional[int] = Query(None, description="Year (defaults to current year)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get leave balance for an employee.
    
    - Employees can see their own balance
    - Admins can see any employee's balance
    """
    leave_service = LeaveService()
    
    # If employee, only show their own balance
    if current_user.role.value == "employee" and current_user.employee_id:
        employee_id = current_user.employee_id
    
    if not employee_id:
        raise_http_exception(
            message="Employee ID is required",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPLOYEE_ID_REQUIRED"
        )
    
    # Verify employee belongs to same company
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise_http_exception(
            message="Employee not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EMPLOYEE_NOT_FOUND"
        )
    
    balances = leave_service.get_leave_balance(
        db=db,
        company_id=current_user.company_id,
        employee_id=employee_id,
        year=year
    )
    
    # Format response
    from decimal import Decimal
    total_available = Decimal(0)
    total_used = Decimal(0)
    total_pending = Decimal(0)
    
    balance_responses = []
    for balance in balances:
        total_available += balance.available_days
        total_used += balance.used_days
        total_pending += balance.pending_days
        
        balance_responses.append(LeaveBalanceResponse(
            id=balance.id,
            company_id=balance.company_id,
            employee_id=balance.employee_id,
            leave_type_id=balance.leave_type_id,
            year=balance.year,
            total_days=balance.total_days,
            used_days=balance.used_days,
            pending_days=balance.pending_days,
            available_days=balance.available_days,
            carried_forward_days=balance.carried_forward_days,
            leave_type_name=balance.leave_type.name if balance.leave_type else None,
            leave_type_code=balance.leave_type.code if balance.leave_type else None,
            employee_name=balance.employee.full_name if balance.employee else None
        ))
    
    return LeaveSummaryResponse(
        employee_id=employee_id,
        employee_name=employee.full_name,
        year=year or date.today().year,
        leave_balances=balance_responses,
        total_available_days=total_available,
        total_used_days=total_used,
        total_pending_days=total_pending
    )


# Leave Calendar Endpoint
@router.get("/calendar", response_model=LeaveCalendarResponse, status_code=status.HTTP_200_OK)
async def get_leave_calendar(
    start_date: date = Query(..., description="Start date for calendar"),
    end_date: date = Query(..., description="End date for calendar"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get leave calendar for a date range.
    
    Shows all approved and pending leaves in the date range.
    """
    leave_service = LeaveService()
    leave_requests = leave_service.get_leave_requests(
        db=db,
        company_id=current_user.company_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Filter only approved and pending
    leave_requests = [lr for lr in leave_requests if lr.status in [LeaveStatus.APPROVED, LeaveStatus.PENDING]]
    
    # Build calendar entries
    calendar_entries = []
    for lr in leave_requests:
        current_date = lr.start_date
        while current_date <= lr.end_date:
            # Only include working days
            if current_date.weekday() < 5:  # Monday to Friday
                calendar_entries.append(LeaveCalendarEntry(
                    date=current_date,
                    employee_id=lr.employee_id,
                    employee_name=lr.employee.full_name if lr.employee else "Unknown",
                    leave_type=lr.leave_type.name if lr.leave_type else "Unknown",
                    leave_type_code=lr.leave_type.code if lr.leave_type else "UNK",
                    status=lr.status.value,
                    number_of_days=1
                ))
            current_date += timedelta(days=1)
    
    return LeaveCalendarResponse(
        start_date=start_date,
        end_date=end_date,
        leaves=calendar_entries
    )


# Leave Type Management Endpoints (Admin Only)
@router.post("/types", response_model=LeaveTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_type(
    leave_type_data: LeaveTypeCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new leave type.
    
    Only admins can create leave types.
    """
    if current_user.role.value != "admin":
        raise_http_exception(
            message="Only admins can create leave types",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED"
        )
    
    from app.api.v1.models.leave_model import LeaveType
    
    # Check if code already exists for this company
    existing = db.query(LeaveType).filter(
        and_(
            LeaveType.company_id == current_user.company_id,
            LeaveType.code == leave_type_data.code
        )
    ).first()
    
    if existing:
        raise_http_exception(
            message=f"Leave type with code '{leave_type_data.code}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LEAVE_TYPE_CODE_EXISTS"
        )
    
    leave_type = LeaveType(
        company_id=current_user.company_id,
        name=leave_type_data.name,
        code=leave_type_data.code,
        description=leave_type_data.description,
        max_days_per_year=leave_type_data.max_days_per_year,
        is_paid=leave_type_data.is_paid,
        requires_approval=leave_type_data.requires_approval,
        can_carry_forward=leave_type_data.can_carry_forward
    )
    
    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)
    
    return LeaveTypeResponse(
        id=leave_type.id,
        company_id=leave_type.company_id,
        name=leave_type.name,
        code=leave_type.code,
        description=leave_type.description,
        max_days_per_year=leave_type.max_days_per_year,
        is_paid=leave_type.is_paid,
        requires_approval=leave_type.requires_approval,
        can_carry_forward=leave_type.can_carry_forward,
        is_active=leave_type.is_active,
        created_at=leave_type.created_at,
        updated_at=leave_type.updated_at
    )


@router.get("/types", response_model=List[LeaveTypeResponse], status_code=status.HTTP_200_OK)
async def get_leave_types(
    active_only: bool = Query(True, description="Show only active leave types"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all leave types for the company.
    """
    from app.api.v1.models.leave_model import LeaveType
    
    query = db.query(LeaveType).filter(LeaveType.company_id == current_user.company_id)
    
    if active_only:
        query = query.filter(LeaveType.is_active == True)
    
    leave_types = query.order_by(LeaveType.name).all()
    
    return [
        LeaveTypeResponse(
            id=lt.id,
            company_id=lt.company_id,
            name=lt.name,
            code=lt.code,
            description=lt.description,
            max_days_per_year=lt.max_days_per_year,
            is_paid=lt.is_paid,
            requires_approval=lt.requires_approval,
            can_carry_forward=lt.can_carry_forward,
            is_active=lt.is_active,
            created_at=lt.created_at,
            updated_at=lt.updated_at
        )
        for lt in leave_types
    ]


@router.put("/types/{leave_type_id}", response_model=LeaveTypeResponse, status_code=status.HTTP_200_OK)
async def update_leave_type(
    leave_type_id: int,
    leave_type_data: LeaveTypeUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update a leave type.
    
    Only admins can update leave types.
    """
    if current_user.role.value != "admin":
        raise_http_exception(
            message="Only admins can update leave types",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED"
        )
    
    from app.api.v1.models.leave_model import LeaveType
    
    leave_type = db.query(LeaveType).filter(
        and_(
            LeaveType.id == leave_type_id,
            LeaveType.company_id == current_user.company_id
        )
    ).first()
    
    if not leave_type:
        raise_http_exception(
            message="Leave type not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LEAVE_TYPE_NOT_FOUND"
        )
    
    # Update fields
    update_data = leave_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(leave_type, field, value)
    
    db.commit()
    db.refresh(leave_type)
    
    return LeaveTypeResponse(
        id=leave_type.id,
        company_id=leave_type.company_id,
        name=leave_type.name,
        code=leave_type.code,
        description=leave_type.description,
        max_days_per_year=leave_type.max_days_per_year,
        is_paid=leave_type.is_paid,
        requires_approval=leave_type.requires_approval,
        can_carry_forward=leave_type.can_carry_forward,
        is_active=leave_type.is_active,
        created_at=leave_type.created_at,
        updated_at=leave_type.updated_at
    )

