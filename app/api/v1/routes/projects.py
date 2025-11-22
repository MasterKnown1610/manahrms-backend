from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
# 
from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.models.user_model import User
from app.api.v1.models.project_model import Project
from app.api.v1.schemas.project_schema import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithTasksResponse
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.schemas.task_schema import TaskResponse
from app.api.v1.models.task_model import TaskStatus, TaskPriority
from app.api.v1.services.project_service import ProjectService
from app.api.v1.services.task_service import TaskService
from app.api.v1.utils.pagination import paginate_query, create_paginated_response


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/create", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Create a new project.
    Only admins can create projects.
    """
    project = ProjectService.create_project(
        db=db,
        company_id=current_user.company_id,
        data=project_data
    )
    
    return ProjectResponse.model_validate(project)


@router.post("/query", response_model=PaginatedResponse[ProjectResponse])
async def query_projects(
    pagination_request: PaginationRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Query projects with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    """
    # Build base query
    query = db.query(Project).filter(Project.company_id == current_user.company_id)
    
    # Apply pagination, filters, and sorting
    items, pagination_info = paginate_query(query, pagination_request, Project)
    
    # Create paginated response
    return create_paginated_response(items, pagination_info, ProjectResponse)


@router.get("/my-projects", response_model=List[ProjectResponse])
async def get_my_projects(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all projects where the current user is the project lead.
    """
    projects = ProjectService.get_projects_by_lead(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id
    )
    
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectWithTasksResponse)
async def get_project_by_id(
    project_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific project by ID with task statistics.
    """
    project = ProjectService.get_project_by_id(
        db=db,
        company_id=current_user.company_id,
        project_id=project_id
    )
    
    # Get task statistics
    task_stats = ProjectService.get_project_task_stats(
        db=db,
        project_id=project_id
    )
    
    project_dict = ProjectResponse.model_validate(project).model_dump()
    project_dict.update({
        'task_count': task_stats['total'],
        'completed_task_count': task_stats['closed'],
        'open_task_count': task_stats['open'] + task_stats['in_progress']
    })
    
    return ProjectWithTasksResponse(**project_dict)


@router.get("/{project_id}/tasks", response_model=PaginatedResponse[TaskResponse])
async def get_project_tasks(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[TaskStatus] = Query(None),
    priority_filter: Optional[TaskPriority] = Query(None),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all tasks for a specific project.
    """
    # Verify project exists and belongs to company
    ProjectService.get_project_by_id(
        db=db,
        company_id=current_user.company_id,
        project_id=project_id
    )
    
    # Get tasks for this project
    items, total = TaskService.list_tasks(
        db=db,
        company_id=current_user.company_id,
        page=page,
        limit=limit,
        status_filter=status_filter,
        priority_filter=priority_filter,
        project_id=project_id
    )
    
    return PaginatedResponse[TaskResponse](
        total=total,
        page=page,
        limit=limit,
        items=[TaskResponse.model_validate(t) for t in items]
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_information(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Update project information.
    Only admins can update projects.
    """
    project = ProjectService.update_project(
        db=db,
        company_id=current_user.company_id,
        project_id=project_id,
        data=project_data
    )
    
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=MessageResponse)
async def deactivate_project(
    project_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Deactivate a project (soft delete).
    Only admins can deactivate projects.
    """
    project = ProjectService.deactivate_project(
        db=db,
        company_id=current_user.company_id,
        project_id=project_id
    )
    
    return MessageResponse(
        message=f"Project '{project.name}' has been deactivated successfully"
    )

