from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from fastapi import HTTPException, status
from datetime import datetime, date, timedelta

from app.api.v1.models.attendance_model import Attendance
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.user_model import User


class AttendanceService:
    """
    Service class for attendance management operations.
    """

    @staticmethod
    def punch_in(
        db: Session,
        company_id: int,
        employee_id: int,
    ) -> Attendance:
        """Punch in for the current day"""
        today = date.today()
        now = datetime.utcnow()
        
        # Check if employee exists and belongs to company
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.company_id == company_id,
            Employee.is_active == True
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
        
        # Check if already punched in today
        existing_attendance = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today
        ).first()
        
        if existing_attendance and existing_attendance.punch_in_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"You have already punched in today at {existing_attendance.punch_in_time.strftime('%H:%M:%S')}",
                    "error_code": "ALREADY_PUNCHED_IN"
                }
            )
        
        # Create or update attendance record
        if existing_attendance:
            existing_attendance.punch_in_time = now
            existing_attendance.is_present = True
            db.commit()
            db.refresh(existing_attendance)
            return existing_attendance
        else:
            attendance = Attendance(
                company_id=company_id,
                employee_id=employee_id,
                attendance_date=today,
                punch_in_time=now,
                is_present=True,
                is_checked_out=False
            )
            db.add(attendance)
            db.commit()
            db.refresh(attendance)
            return attendance

    @staticmethod
    def punch_out(
        db: Session,
        company_id: int,
        employee_id: int,
    ) -> Attendance:
        """Punch out for the current day"""
        today = date.today()
        now = datetime.utcnow()
        
        # Check if employee exists and belongs to company
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.company_id == company_id,
            Employee.is_active == True
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
        
        # Find today's attendance record
        attendance = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today
        ).first()
        
        if not attendance or not attendance.punch_in_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "You must punch in before punching out",
                    "error_code": "NO_PUNCH_IN"
                }
            )
        
        if attendance.punch_out_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"You have already punched out today at {attendance.punch_out_time.strftime('%H:%M:%S')}",
                    "error_code": "ALREADY_PUNCHED_OUT"
                }
            )
        
        # Update punch out time
        attendance.punch_out_time = now
        attendance.is_checked_out = True
        
        # Calculate work duration
        duration = attendance.calculate_work_duration()
        if duration:
            attendance.work_duration_hours = duration
        
        db.commit()
        db.refresh(attendance)
        return attendance

    @staticmethod
    def get_today_attendance(
        db: Session,
        company_id: int,
        employee_id: int,
    ) -> Optional[Attendance]:
        """Get today's attendance record for an employee"""
        today = date.today()
        return db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today
        ).first()

    @staticmethod
    def get_attendance_calendar(
        db: Session,
        company_id: int,
        employee_id: int,
        year: int,
        month: int,
    ) -> Tuple[List[Attendance], int, float]:
        """Get attendance calendar for a specific month"""
        # Validate employee belongs to company
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.company_id == company_id,
            Employee.is_active == True
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
        
        # Get all attendance records for the month
        start_date = date(year, month, 1)
        # Get last day of month
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        attendances = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.employee_id == employee_id,
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date
        ).order_by(Attendance.attendance_date).all()
        
        # Calculate statistics
        present_days = sum(1 for a in attendances if a.is_present)
        total_minutes = sum(
            a.work_duration_hours for a in attendances 
            if a.work_duration_hours is not None
        )
        total_hours = total_minutes / 60.0 if total_minutes else 0.0
        
        return attendances, present_days, total_hours

    @staticmethod
    def get_attendance_stats(
        db: Session,
        company_id: int,
        target_date: Optional[date] = None,
    ) -> dict:
        """Get attendance statistics for a specific date (default: today)"""
        if target_date is None:
            target_date = date.today()
        
        # Get total active employees
        total_employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True
        ).count()
        
        # Get present employees (punched in)
        present_employees = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.attendance_date == target_date,
            Attendance.is_present == True
        ).count()
        
        # Get employees who punched in but not out
        checked_in_not_out = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.attendance_date == target_date,
            Attendance.is_present == True,
            Attendance.is_checked_out == False
        ).count()
        
        absent_employees = total_employees - present_employees
        
        return {
            "total_employees": total_employees,
            "present_today": present_employees,
            "absent_today": absent_employees,
            "checked_in_but_not_out": checked_in_not_out
        }

    @staticmethod
    def list_attendance_records(
        db: Session,
        company_id: int,
        employee_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[Attendance], int]:
        """List attendance records with filters"""
        query = db.query(Attendance).filter(
            Attendance.company_id == company_id
        )
        
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)
        
        if start_date:
            query = query.filter(Attendance.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(Attendance.attendance_date <= end_date)
        
        total = query.count()
        items = query.order_by(
            Attendance.attendance_date.desc(),
            Attendance.punch_in_time.desc()
        ).offset((page - 1) * limit).limit(limit).all()
        
        return items, total

