from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.schemas.dashboard_schema import DashboardResponse
from app.api.v1.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardResponse)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get complete dashboard overview with all statistics and recent activities.
    Returns comprehensive dashboard data including:
    - Overview statistics (employees, tasks, projects, departments)
    - Task statistics (by status, priority, deadlines)
    - Employee statistics (by department)
    - Today's attendance statistics
    - Leave statistics
    - Project statistics
    - Recent tasks
    - Upcoming deadlines
    - Recent activities
    """
    dashboard_data = DashboardService.get_dashboard_data(db, current_user.company_id)
    return DashboardResponse(**dashboard_data)


@router.get("/stats/overview")
async def get_overview_stats(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get overview statistics only"""
    return DashboardService.get_overview_stats(db, current_user.company_id)


@router.get("/stats/tasks")
async def get_task_statistics(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get task statistics breakdown"""
    return DashboardService.get_task_stats(db, current_user.company_id)


@router.get("/stats/employees")
async def get_employee_statistics(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get employee statistics"""
    return DashboardService.get_employee_stats(db, current_user.company_id)


@router.get("/stats/attendance")
async def get_attendance_statistics(
    target_date: Optional[date] = Query(None, description="Target date (defaults to today)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get attendance statistics for a specific date"""
    return DashboardService.get_attendance_stats(db, current_user.company_id, target_date)


@router.get("/stats/leaves")
async def get_leave_statistics(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get leave statistics"""
    return DashboardService.get_leave_stats(db, current_user.company_id)


@router.get("/stats/projects")
async def get_project_statistics(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get project statistics"""
    return DashboardService.get_project_stats(db, current_user.company_id)


@router.get("/recent/tasks")
async def get_recent_tasks(
    limit: int = Query(5, ge=1, le=20, description="Number of recent tasks to return"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get recent tasks"""
    return DashboardService.get_recent_tasks(db, current_user.company_id, limit)


@router.get("/recent/deadlines")
async def get_upcoming_deadlines(
    limit: int = Query(5, ge=1, le=20, description="Number of upcoming deadlines to return"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get upcoming task deadlines"""
    return DashboardService.get_upcoming_deadlines(db, current_user.company_id, limit)


@router.get("/recent/activities")
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="Number of recent activities to return"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """Get recent activities across different entities"""
    return DashboardService.get_recent_activities(db, current_user.company_id, limit)

