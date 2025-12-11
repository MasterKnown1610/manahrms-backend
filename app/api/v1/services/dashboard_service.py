from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from app.api.v1.models.employee_model import Employee
from app.api.v1.models.department_model import Department
from app.api.v1.models.task_model import Task, TaskStatus, TaskPriority
from app.api.v1.models.project_model import Project
from app.api.v1.models.attendance_model import Attendance
from app.api.v1.models.leave_model import LeaveRequest, LeaveStatus, LeaveBalance, LeaveType
from app.api.v1.models.user_model import User


class DashboardService:
    """Service for dashboard statistics and data"""

    @staticmethod
    def get_overview_stats(db: Session, company_id: int, employee_id: Optional[int] = None) -> Dict:
        """Get overview statistics"""
        today = date.today()
        
        # Employee stats
        total_employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)
        ).count()
        
        active_employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).count()
        
        # Department stats
        total_departments = db.query(Department).filter(
            Department.company_id == company_id
        ).count()
        
        # Project stats
        total_projects = db.query(Project).filter(
            Project.company_id == company_id
        ).count()
        
        active_projects = db.query(Project).filter(
            Project.company_id == company_id,
            Project.is_active == True
        ).count()
        
        # Task stats - filter by employee_id if provided
        task_query = db.query(Task).filter(Task.company_id == company_id)
        if employee_id:
            task_query = task_query.filter(Task.assigned_to_employee_id == employee_id)
        
        total_tasks = task_query.count()
        
        open_tasks = task_query.filter(Task.status == TaskStatus.OPEN).count()
        
        in_progress_tasks = task_query.filter(Task.status == TaskStatus.IN_PROGRESS).count()
        
        closed_tasks = task_query.filter(Task.status == TaskStatus.CLOSED).count()
        
        overdue_tasks = task_query.filter(
            Task.due_date < today,
            Task.status != TaskStatus.CLOSED
        ).count()
        
        # Leave stats
        pending_leave_requests = db.query(LeaveRequest).filter(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status == LeaveStatus.PENDING
        ).count()
        
        return {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "total_departments": total_departments,
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
            "in_progress_tasks": in_progress_tasks,
            "closed_tasks": closed_tasks,
            "overdue_tasks": overdue_tasks,
            "pending_leave_requests": pending_leave_requests
        }

    @staticmethod
    def get_task_stats(db: Session, company_id: int, employee_id: Optional[int] = None) -> Dict:
        """Get task statistics breakdown"""
        today = date.today()
        week_end = today + timedelta(days=7)
        
        # Base task query - filter by employee_id if provided
        base_task_filter = Task.company_id == company_id
        if employee_id:
            base_task_filter = and_(base_task_filter, Task.assigned_to_employee_id == employee_id)
        
        # Tasks by status
        status_counts = db.query(
            Task.status,
            func.count(Task.id).label('count')
        ).filter(
            base_task_filter
        ).group_by(Task.status).all()
        
        by_status = {status.value: 0 for status in TaskStatus}
        for status, count in status_counts:
            by_status[status.value] = count
        
        # Tasks by priority
        priority_counts = db.query(
            Task.priority,
            func.count(Task.id).label('count')
        ).filter(
            base_task_filter
        ).group_by(Task.priority).all()
        
        by_priority = {priority.value: 0 for priority in TaskPriority}
        for priority, count in priority_counts:
            by_priority[priority.value] = count
        
        # Overdue tasks
        overdue_query = db.query(Task).filter(
            base_task_filter,
            Task.due_date < today,
            Task.status != TaskStatus.CLOSED
        )
        overdue_count = overdue_query.count()
        
        # Due today
        due_today_count = db.query(Task).filter(
            base_task_filter,
            Task.due_date == today,
            Task.status != TaskStatus.CLOSED
        ).count()
        
        # Due this week
        due_this_week_count = db.query(Task).filter(
            base_task_filter,
            Task.due_date >= today,
            Task.due_date <= week_end,
            Task.status != TaskStatus.CLOSED
        ).count()
        
        return {
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_count": overdue_count,
            "due_today_count": due_today_count,
            "due_this_week_count": due_this_week_count
        }

    @staticmethod
    def get_employee_stats(db: Session, company_id: int) -> Dict:
        """Get employee statistics"""
        total = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)
        ).count()
        
        active = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).count()
        
        # Employees by department
        dept_counts = db.query(
            Department.name,
            func.count(Employee.id).label('count')
        ).join(
            Employee, Department.id == Employee.department_id
        ).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).group_by(Department.name).all()
        
        by_department = {name: count for name, count in dept_counts}
        
        return {
            "total": total,
            "active": active,
            "by_department": by_department
        }

    @staticmethod
    def get_attendance_stats(db: Session, company_id: int, target_date: Optional[date] = None) -> Dict:
        """Get today's attendance statistics"""
        if target_date is None:
            target_date = date.today()
        
        total_employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).count()
        
        present_today = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.attendance_date == target_date,
            Attendance.is_present == True
        ).count()
        
        checked_in_not_out = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.attendance_date == target_date,
            Attendance.is_present == True,
            Attendance.is_checked_out == False
        ).count()
        
        absent_today = total_employees - present_today
        
        attendance_percentage = (present_today / total_employees * 100) if total_employees > 0 else 0.0
        
        return {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "checked_in_not_out": checked_in_not_out,
            "attendance_percentage": round(attendance_percentage, 2)
        }

    @staticmethod
    def get_leave_stats(db: Session, company_id: int) -> Dict:
        """Get leave statistics"""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        # Status counts
        status_counts = db.query(
            LeaveRequest.status,
            func.count(LeaveRequest.id).label('count')
        ).filter(
            LeaveRequest.company_id == company_id
        ).group_by(LeaveRequest.status).all()
        
        by_status = {status.value: 0 for status in LeaveStatus}
        for status, count in status_counts:
            by_status[status.value] = count
        
        # Approved this month
        approved_this_month = db.query(LeaveRequest).filter(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.approved_date >= datetime.combine(month_start, datetime.min.time())
        ).count()
        
        # Rejected this month
        rejected_this_month = db.query(LeaveRequest).filter(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status == LeaveStatus.REJECTED,
            LeaveRequest.approved_date >= datetime.combine(month_start, datetime.min.time())
        ).count()
        
        return {
            "pending_requests": by_status.get(LeaveStatus.PENDING.value, 0),
            "approved_this_month": approved_this_month,
            "rejected_this_month": rejected_this_month,
            "by_status": by_status
        }

    @staticmethod
    def get_project_stats(db: Session, company_id: int) -> Dict:
        """Get project statistics"""
        today = date.today()
        
        total = db.query(Project).filter(
            Project.company_id == company_id
        ).count()
        
        active = db.query(Project).filter(
            Project.company_id == company_id,
            Project.is_active == True
        ).count()
        
        completed = db.query(Project).filter(
            Project.company_id == company_id,
            Project.is_active == False
        ).count()
        
        overdue = db.query(Project).filter(
            Project.company_id == company_id,
            Project.target_date < today,
            Project.is_active == True
        ).count()
        
        return {
            "total": total,
            "active": active,
            "completed": completed,
            "overdue": overdue
        }

    @staticmethod
    def get_recent_tasks(db: Session, company_id: int, limit: int = 5, employee_id: Optional[int] = None) -> List[Dict]:
        """Get recent tasks"""
        query = db.query(Task).outerjoin(
            Employee, Task.assigned_to_employee_id == Employee.id
        ).filter(
            Task.company_id == company_id
        )
        
        # Filter by employee_id if provided
        if employee_id:
            query = query.filter(Task.assigned_to_employee_id == employee_id)
        
        tasks = query.order_by(
            Task.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date,
                "assigned_to_employee_name": task.assigned_to_employee.full_name if task.assigned_to_employee else None,
                "created_at": task.created_at
            })
        
        return result

    @staticmethod
    def get_upcoming_deadlines(db: Session, company_id: int, limit: int = 5, employee_id: Optional[int] = None) -> List[Dict]:
        """Get upcoming task deadlines"""
        today = date.today()
        future_date = today + timedelta(days=30)  # Next 30 days
        
        query = db.query(Task).outerjoin(
            Employee, Task.assigned_to_employee_id == Employee.id
        ).filter(
            Task.company_id == company_id,
            Task.due_date >= today,
            Task.due_date <= future_date,
            Task.status != TaskStatus.CLOSED
        )
        
        # Filter by employee_id if provided
        if employee_id:
            query = query.filter(Task.assigned_to_employee_id == employee_id)
        
        tasks = query.order_by(
            Task.due_date.asc()
        ).limit(limit).all()
        
        result = []
        for task in tasks:
            days_until_due = (task.due_date - today).days
            result.append({
                "id": task.id,
                "title": task.title,
                "due_date": task.due_date,
                "priority": task.priority,
                "assigned_to_employee_name": task.assigned_to_employee.full_name if task.assigned_to_employee else None,
                "days_until_due": days_until_due
            })
        
        return result

    @staticmethod
    def get_recent_activities(db: Session, company_id: int, limit: int = 10) -> List[Dict]:
        """Get recent activities across different entities"""
        activities = []
        
        # Recent tasks
        recent_tasks = db.query(Task).outerjoin(
            User, Task.created_by_user_id == User.id
        ).filter(
            Task.company_id == company_id
        ).order_by(Task.created_at.desc()).limit(limit // 3).all()
        
        for task in recent_tasks:
            activities.append({
                "type": "task_created",
                "title": f"Task: {task.title}",
                "description": f"New task created with status {task.status.value}",
                "timestamp": task.created_at,
                "user_name": task.created_by_user.full_name if task.created_by_user else None
            })
        
        # Recent employees
        recent_employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)
        ).order_by(Employee.created_at.desc()).limit(limit // 3).all()
        
        for emp in recent_employees:
            activities.append({
                "type": "employee_added",
                "title": f"Employee: {emp.full_name}",
                "description": f"New employee {emp.employee_code} added",
                "timestamp": emp.created_at,
                "user_name": None
            })
        
        # Recent projects
        recent_projects = db.query(Project).outerjoin(
            User, Project.project_lead_id == User.id
        ).filter(
            Project.company_id == company_id
        ).order_by(Project.created_at.desc()).limit(limit // 3).all()
        
        for project in recent_projects:
            activities.append({
                "type": "project_created",
                "title": f"Project: {project.name}",
                "description": f"New project for {project.client}",
                "timestamp": project.created_at,
                "user_name": project.project_lead.full_name if project.project_lead else None
            })
        
        # Sort by timestamp and return most recent
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

    @staticmethod
    def get_dashboard_data(db: Session, company_id: int, employee_id: Optional[int] = None) -> Dict:
        """Get complete dashboard data"""
        return {
            "overview": DashboardService.get_overview_stats(db, company_id, employee_id),
            "task_stats": DashboardService.get_task_stats(db, company_id, employee_id),
            "employee_stats": DashboardService.get_employee_stats(db, company_id),
            "attendance_stats": DashboardService.get_attendance_stats(db, company_id),
            "leave_stats": DashboardService.get_leave_stats(db, company_id),
            "project_stats": DashboardService.get_project_stats(db, company_id),
            "recent_tasks": DashboardService.get_recent_tasks(db, company_id, limit=5, employee_id=employee_id),
            "upcoming_deadlines": DashboardService.get_upcoming_deadlines(db, company_id, limit=5, employee_id=employee_id),
            "recent_activities": DashboardService.get_recent_activities(db, company_id)
        }

    @staticmethod
    def get_employee_dashboard_data(db: Session, company_id: int, employee_id: int) -> Dict:
        """Get employee-specific dashboard data"""
        today = date.today()
        current_year = today.year
        
        # Base filter for employee tasks
        base_task_filter = and_(
            Task.company_id == company_id,
            Task.assigned_to_employee_id == employee_id
        )
        
        # My Tasks - total count
        my_tasks_count = db.query(Task).filter(base_task_filter).count()
        
        # Task counts by status
        open_tasks = db.query(Task).filter(
            base_task_filter,
            Task.status == TaskStatus.OPEN
        ).count()
        
        in_progress_tasks = db.query(Task).filter(
            base_task_filter,
            Task.status == TaskStatus.IN_PROGRESS
        ).count()
        
        completed_tasks = db.query(Task).filter(
            base_task_filter,
            Task.status == TaskStatus.CLOSED
        ).count()
        
        # Today's Status - attendance
        today_attendance = db.query(Attendance).filter(
            Attendance.company_id == company_id,
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today
        ).first()
        
        today_status = {
            "is_present": False,
            "is_checked_in": False,
            "is_checked_out": False,
            "punch_in_time": None,
            "punch_out_time": None,
            "work_duration_hours": None
        }
        
        if today_attendance:
            today_status = {
                "is_present": today_attendance.is_present,
                "is_checked_in": today_attendance.is_present,
                "is_checked_out": today_attendance.is_checked_out,
                "punch_in_time": today_attendance.punch_in_time.isoformat() if today_attendance.punch_in_time else None,
                "punch_out_time": today_attendance.punch_out_time.isoformat() if today_attendance.punch_out_time else None,
                "work_duration_hours": today_attendance.work_duration_hours / 60.0 if today_attendance.work_duration_hours else None
            }
        
        # Leave Balance - get all leave balances for current year with leave type
        leave_balances = db.query(LeaveBalance).join(
            LeaveType, LeaveBalance.leave_type_id == LeaveType.id
        ).filter(
            LeaveBalance.company_id == company_id,
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == current_year
        ).all()
        
        leave_balance_list = []
        total_available_days = 0.0
        for balance in leave_balances:
            leave_balance_list.append({
                "leave_type_id": balance.leave_type_id,
                "leave_type_name": balance.leave_type.name if balance.leave_type else None,
                "total_days": float(balance.total_days),
                "used_days": float(balance.used_days),
                "pending_days": float(balance.pending_days),
                "available_days": float(balance.available_days),
                "carried_forward_days": float(balance.carried_forward_days)
            })
            total_available_days += float(balance.available_days)
        
        # My Projects - projects that have tasks assigned to this employee
        my_projects = db.query(Project).join(
            Task, Project.id == Task.project_id
        ).filter(
            Project.company_id == company_id,
            Task.assigned_to_employee_id == employee_id
        ).distinct().all()
        
        my_projects_list = []
        for project in my_projects:
            # Count tasks for this project assigned to this employee
            project_tasks_count = db.query(Task).filter(
                Task.project_id == project.id,
                Task.assigned_to_employee_id == employee_id
            ).count()
            
            my_projects_list.append({
                "id": project.id,
                "name": project.name,
                "client": project.client,
                "target_date": project.target_date.isoformat() if project.target_date else None,
                "is_active": project.is_active,
                "tasks_count": project_tasks_count
            })
        
        # Recent Tasks
        recent_tasks = DashboardService.get_recent_tasks(db, company_id, limit=10, employee_id=employee_id)
        
        # Upcoming Deadlines
        upcoming_deadlines = DashboardService.get_upcoming_deadlines(db, company_id, limit=10, employee_id=employee_id)
        
        return {
            "my_tasks": my_tasks_count,
            "today_status": today_status,
            "leave_balance": {
                "total_available_days": total_available_days,
                "by_leave_type": leave_balance_list
            },
            "my_projects": my_projects_list,
            "open_tasks": open_tasks,
            "in_progress": in_progress_tasks,
            "completed": completed_tasks,
            "recent_tasks": recent_tasks,
            "upcoming_deadlines": upcoming_deadlines
        }

