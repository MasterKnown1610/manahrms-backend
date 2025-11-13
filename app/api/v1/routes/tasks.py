from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api.v1.dependencies import get_current_user, require_admin
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.task_model import TaskStatus, TaskPriority
from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
)
from app.api.v1.services.task_service import TaskService


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = TaskService.create_task(
        db=db,
        company_id=current_user.company_id,
        creator_user_id=current_user.id,
        data=data,
    )
    return TaskResponse.model_validate(task)


@router.get("/", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[TaskStatus] = Query(None),
    priority_filter: Optional[TaskPriority] = Query(None),
    assigned_to_employee_id: Optional[int] = Query(None),
    only_mine: bool = Query(False, description="Employees: limit to tasks assigned to me"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    only_mine_employee_id = None
    if only_mine and current_user.role == UserRole.EMPLOYEE and current_user.employee_id:
        only_mine_employee_id = current_user.employee_id

    items, total = TaskService.list_tasks(
        db=db,
        company_id=current_user.company_id,
        page=page,
        limit=limit,
        status_filter=status_filter,
        priority_filter=priority_filter,
        assigned_to_employee_id=assigned_to_employee_id,
        only_mine_employee_id=only_mine_employee_id,
    )

    return PaginatedResponse[TaskResponse](
        total=total,
        page=page,
        limit=limit,
        items=[TaskResponse.model_validate(t) for t in items],
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
async def close_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)

    # Admins can close any task; employees can close only their own
    if current_user.role == UserRole.EMPLOYEE and task.assigned_to_employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to close this task")

    closed = TaskService.close_task(db, current_user.company_id, task_id)
    return TaskResponse.model_validate(closed)


