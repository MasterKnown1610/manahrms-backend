from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from app.api.v1.models.task_model import TaskStatus, TaskPriority
from app.api.v1.models.leave_model import LeaveStatus


class OverviewStats(BaseModel):
    """Overview statistics for dashboard"""
    total_employees: int
    active_employees: int
    total_departments: int
    total_projects: int
    active_projects: int
    total_tasks: int
    open_tasks: int
    in_progress_tasks: int
    closed_tasks: int
    overdue_tasks: int
    pending_leave_requests: int


class TaskStats(BaseModel):
    """Task statistics breakdown"""
    by_status: dict[str, int]  # {"open": 10, "in_progress": 5, "closed": 20}
    by_priority: dict[str, int]  # {"low": 5, "medium": 15, "high": 10}
    overdue_count: int
    due_today_count: int
    due_this_week_count: int


class EmployeeStats(BaseModel):
    """Employee statistics"""
    total: int
    active: int
    by_department: dict[str, int]  # {"IT": 10, "HR": 5}


class AttendanceStats(BaseModel):
    """Today's attendance statistics"""
    total_employees: int
    present_today: int
    absent_today: int
    checked_in_not_out: int
    attendance_percentage: float


class LeaveStats(BaseModel):
    """Leave statistics"""
    pending_requests: int
    approved_this_month: int
    rejected_this_month: int
    by_status: dict[str, int]  # {"pending": 5, "approved": 10, "rejected": 2}


class ProjectStats(BaseModel):
    """Project statistics"""
    total: int
    active: int
    completed: int
    overdue: int


class RecentTask(BaseModel):
    """Recent task information"""
    id: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date]
    assigned_to_employee_name: Optional[str]
    created_at: datetime


class UpcomingDeadline(BaseModel):
    """Upcoming deadline information"""
    id: int
    title: str
    due_date: date
    priority: TaskPriority
    assigned_to_employee_name: Optional[str]
    days_until_due: int


class RecentActivity(BaseModel):
    """Recent activity information"""
    type: str  # "task_created", "task_updated", "employee_added", "project_created"
    title: str
    description: str
    timestamp: datetime
    user_name: Optional[str]


class DashboardResponse(BaseModel):
    """Complete dashboard response"""
    overview: OverviewStats
    task_stats: TaskStats
    employee_stats: EmployeeStats
    attendance_stats: AttendanceStats
    leave_stats: LeaveStats
    project_stats: ProjectStats
    recent_tasks: List[RecentTask]
    upcoming_deadlines: List[UpcomingDeadline]
    recent_activities: List[RecentActivity]


# Employee Dashboard Schemas
class TodayStatus(BaseModel):
    """Today's attendance status"""
    is_present: bool
    is_checked_in: bool
    is_checked_out: bool
    punch_in_time: Optional[str]
    punch_out_time: Optional[str]
    work_duration_hours: Optional[float]


class LeaveBalanceItem(BaseModel):
    """Leave balance for a specific leave type"""
    leave_type_id: int
    leave_type_name: Optional[str]
    total_days: float
    used_days: float
    pending_days: float
    available_days: float
    carried_forward_days: float


class LeaveBalanceInfo(BaseModel):
    """Leave balance information"""
    total_available_days: float
    by_leave_type: List[LeaveBalanceItem]


class MyProject(BaseModel):
    """Project information for employee"""
    id: int
    name: str
    client: str
    target_date: Optional[str]
    is_active: bool
    tasks_count: int


class EmployeeDashboardResponse(BaseModel):
    """Employee dashboard response"""
    my_tasks: int
    today_status: TodayStatus
    leave_balance: LeaveBalanceInfo
    my_projects: List[MyProject]
    open_tasks: int
    in_progress: int
    completed: int
    recent_tasks: List[RecentTask]
    upcoming_deadlines: List[UpcomingDeadline]

