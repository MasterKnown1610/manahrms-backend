from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.task_model import TaskStatus, TaskPriority, Task
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
)
from app.api.v1.services.task_service import TaskService
from app.api.v1.utils.pagination import paginate_query, create_paginated_response


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    data: TaskCreate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    task = TaskService.create_task(
        db=db,
        company_id=current_user.company_id,
        creator_user_id=current_user.id,
        data=data,
    )
    return TaskResponse.model_validate(task)


@router.post("/query", response_model=PaginatedResponse[TaskResponse])
async def query_tasks(
    pagination_request: PaginationRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Query tasks with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    """
    # Build base query
    query = db.query(Task).filter(Task.company_id == current_user.company_id)
    
    # For employees, optionally filter to only their tasks
    # This can be done via filter in the request payload
    # If employee wants only their tasks, they can add filter: [{"field": "assigned_to_employee_id", "operator": "eq", "value": employee_id}]
    
    # Apply pagination, filters, and sorting
    items, pagination_info = paginate_query(query, pagination_request, Task)
    
    # Create paginated response
    return create_paginated_response(items, pagination_info, TaskResponse)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task_information(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    # Allow admins to update any task; employees can update only their own assigned tasks (no reassignment)
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)
    if current_user.role == UserRole.EMPLOYEE:
        if task.assigned_to_employee_id != current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task")
        # prevent employee from reassigning or changing company/creator
        if data.assigned_to_employee_id is not None and data.assigned_to_employee_id != task.assigned_to_employee_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employees cannot reassign tasks")

    updated = TaskService.update_task(db, current_user.company_id, task_id, data)
    return TaskResponse.model_validate(updated)


@router.post("/{task_id}/close", response_model=TaskResponse)
async def close_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)

    # Admins can close any task; employees can close only their own
    if current_user.role == UserRole.EMPLOYEE and task.assigned_to_employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to close this task")

    closed = TaskService.close_task(db, current_user.company_id, task_id)
    return TaskResponse.model_validate(closed)


