"""
Leave Management Service
Handles leave requests, approvals, and balance calculations
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.api.v1.models.leave_model import LeaveType, LeaveRequest, LeaveBalance, LeaveStatus
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.user_model import User
from app.api.v1.utils.error_handler import raise_http_exception
from fastapi import status


class LeaveService:
    """Service for managing employee leaves"""
    
    def __init__(self):
        pass
    
    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        """
        Calculate number of working days between two dates (inclusive).
        Excludes weekends (Saturday, Sunday).
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Number of working days
        """
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        current_date = start_date
        working_days = 0
        
        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    def get_or_create_leave_balance(
        self,
        db: Session,
        company_id: int,
        employee_id: int,
        leave_type_id: int,
        year: int
    ) -> LeaveBalance:
        """
        Get or create leave balance for an employee for a specific leave type and year.
        
        Args:
            db: Database session
            company_id: Company ID
            employee_id: Employee ID
            leave_type_id: Leave type ID
            year: Year
            
        Returns:
            LeaveBalance object
        """
        balance = db.query(LeaveBalance).filter(
            and_(
                LeaveBalance.company_id == company_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type_id == leave_type_id,
                LeaveBalance.year == year
            )
        ).first()
        
        if not balance:
            # Get leave type to get max_days_per_year
            leave_type = db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
            total_days = Decimal(leave_type.max_days_per_year) if leave_type and leave_type.max_days_per_year else Decimal(0)
            
            balance = LeaveBalance(
                company_id=company_id,
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                year=year,
                total_days=total_days,
                used_days=Decimal(0),
                pending_days=Decimal(0),
                available_days=total_days,
                carried_forward_days=Decimal(0)
            )
            db.add(balance)
            db.commit()
            db.refresh(balance)
        
        return balance
    
    def apply_for_leave(
        self,
        db: Session,
        company_id: int,
        employee_id: int,
        leave_type_id: int,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None
    ) -> LeaveRequest:
        """
        Apply for leave.
        
        Args:
            db: Database session
            company_id: Company ID
            employee_id: Employee ID
            leave_type_id: Leave type ID
            start_date: Start date
            end_date: End date
            reason: Reason for leave
            
        Returns:
            LeaveRequest object
        """
        # Validate dates
        if start_date > end_date:
            raise_http_exception(
                message="Start date cannot be after end date",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_DATE_RANGE"
            )
        
        if start_date < date.today():
            raise_http_exception(
                message="Cannot apply for leave in the past",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_DATE_PAST"
            )
        
        # Verify leave type exists and is active
        leave_type = db.query(LeaveType).filter(
            and_(
                LeaveType.id == leave_type_id,
                LeaveType.company_id == company_id,
                LeaveType.is_active == True
            )
        ).first()
        
        if not leave_type:
            raise_http_exception(
                message="Leave type not found or inactive",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="LEAVE_TYPE_NOT_FOUND"
            )
        
        # Calculate number of days
        number_of_days = self.calculate_working_days(start_date, end_date)
        
        if number_of_days <= 0:
            raise_http_exception(
                message="Invalid date range: no working days",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_DATE_RANGE"
            )
        
        # Check leave balance
        current_year = date.today().year
        balance = self.get_or_create_leave_balance(
            db, company_id, employee_id, leave_type_id, current_year
        )
        
        # Check if enough balance available
        available = balance.available_days - balance.pending_days
        if available < Decimal(number_of_days):
            raise_http_exception(
                message=f"Insufficient leave balance. Available: {available} days, Requested: {number_of_days} days",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INSUFFICIENT_LEAVE_BALANCE"
            )
        
        # Create leave request
        leave_request = LeaveRequest(
            company_id=company_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            number_of_days=number_of_days,
            reason=reason,
            status=LeaveStatus.PENDING
        )
        
        db.add(leave_request)
        
        # Update leave balance - add to pending days
        balance.pending_days += Decimal(number_of_days)
        balance.available_days = balance.total_days - balance.used_days - balance.pending_days
        
        db.commit()
        db.refresh(leave_request)
        
        return leave_request
    
    def approve_leave(
        self,
        db: Session,
        leave_request_id: int,
        approver_user_id: int,
        approved: bool,
        rejection_reason: Optional[str] = None
    ) -> LeaveRequest:
        """
        Approve or reject a leave request.
        
        Args:
            db: Database session
            leave_request_id: Leave request ID
            approver_user_id: User ID of approver
            approved: True to approve, False to reject
            rejection_reason: Reason for rejection (if rejected)
            
        Returns:
            Updated LeaveRequest object
        """
        leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
        
        if not leave_request:
            raise_http_exception(
                message="Leave request not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="LEAVE_REQUEST_NOT_FOUND"
            )
        
        if leave_request.status != LeaveStatus.PENDING:
            raise_http_exception(
                message=f"Leave request is already {leave_request.status.value}",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="LEAVE_REQUEST_ALREADY_PROCESSED"
            )
        
        # Update leave request
        if approved:
            leave_request.status = LeaveStatus.APPROVED
            leave_request.approved_date = datetime.utcnow()
            leave_request.rejection_reason = None
        else:
            leave_request.status = LeaveStatus.REJECTED
            leave_request.approved_date = datetime.utcnow()
            leave_request.rejection_reason = rejection_reason
        
        leave_request.approved_by_user_id = approver_user_id
        
        # Update leave balance
        balance = self.get_or_create_leave_balance(
            db,
            leave_request.company_id,
            leave_request.employee_id,
            leave_request.leave_type_id,
            leave_request.start_date.year
        )
        
        if approved:
            # Move from pending to used
            balance.pending_days -= Decimal(leave_request.number_of_days)
            balance.used_days += Decimal(leave_request.number_of_days)
        else:
            # Remove from pending (rejected)
            balance.pending_days -= Decimal(leave_request.number_of_days)
        
        balance.available_days = balance.total_days - balance.used_days - balance.pending_days
        
        db.commit()
        db.refresh(leave_request)
        
        return leave_request
    
    def get_leave_balance(
        self,
        db: Session,
        company_id: int,
        employee_id: int,
        year: Optional[int] = None
    ) -> List[LeaveBalance]:
        """
        Get leave balance for an employee.
        
        Args:
            db: Database session
            company_id: Company ID
            employee_id: Employee ID
            year: Year (defaults to current year)
            
        Returns:
            List of LeaveBalance objects
        """
        if year is None:
            year = date.today().year
        
        balances = db.query(LeaveBalance).filter(
            and_(
                LeaveBalance.company_id == company_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year
            )
        ).all()
        
        # If no balances exist, create them for all active leave types
        if not balances:
            leave_types = db.query(LeaveType).filter(
                and_(
                    LeaveType.company_id == company_id,
                    LeaveType.is_active == True
                )
            ).all()
            
            for leave_type in leave_types:
                balance = self.get_or_create_leave_balance(
                    db, company_id, employee_id, leave_type.id, year
                )
                balances.append(balance)
        
        return balances
    
    def get_leave_requests(
        self,
        db: Session,
        company_id: int,
        employee_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[LeaveRequest]:
        """
        Get leave requests with filters.
        
        Args:
            db: Database session
            company_id: Company ID
            employee_id: Employee ID (optional filter)
            status: Status filter (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            
        Returns:
            List of LeaveRequest objects
        """
        query = db.query(LeaveRequest).filter(LeaveRequest.company_id == company_id)
        
        if employee_id:
            query = query.filter(LeaveRequest.employee_id == employee_id)
        
        if status:
            try:
                status_enum = LeaveStatus(status)
                query = query.filter(LeaveRequest.status == status_enum)
            except ValueError:
                pass
        
        if start_date:
            query = query.filter(LeaveRequest.start_date >= start_date)
        
        if end_date:
            query = query.filter(LeaveRequest.end_date <= end_date)
        
        return query.order_by(LeaveRequest.applied_date.desc()).all()
    
    def cancel_leave_request(
        self,
        db: Session,
        leave_request_id: int,
        employee_id: int
    ) -> LeaveRequest:
        """
        Cancel a leave request (only by the employee who applied).
        
        Args:
            db: Database session
            leave_request_id: Leave request ID
            employee_id: Employee ID (must match request owner)
            
        Returns:
            Updated LeaveRequest object
        """
        leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
        
        if not leave_request:
            raise_http_exception(
                message="Leave request not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="LEAVE_REQUEST_NOT_FOUND"
            )
        
        if leave_request.employee_id != employee_id:
            raise_http_exception(
                message="You can only cancel your own leave requests",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="PERMISSION_DENIED"
            )
        
        if leave_request.status != LeaveStatus.PENDING:
            raise_http_exception(
                message="Can only cancel pending leave requests",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="CANNOT_CANCEL_PROCESSED_REQUEST"
            )
        
        # Update status
        leave_request.status = LeaveStatus.CANCELLED
        
        # Update leave balance - remove from pending
        balance = self.get_or_create_leave_balance(
            db,
            leave_request.company_id,
            leave_request.employee_id,
            leave_request.leave_type_id,
            leave_request.start_date.year
        )
        
        balance.pending_days -= Decimal(leave_request.number_of_days)
        balance.available_days = balance.total_days - balance.used_days - balance.pending_days
        
        db.commit()
        db.refresh(leave_request)
        
        return leave_request

