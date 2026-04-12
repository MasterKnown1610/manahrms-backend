from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.task_model import TaskStatus, TaskPriority, Task
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest, PaginationInfo
from app.api.v1.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskDetailResponse,
    TaskCommentCreate,
    TaskCommentUpdate,
    TaskCommentResponse,
    TaskCommitCreate,
    TaskCommitResponse,
    TaskPermissionGrant,
    TaskPermissionResponse,
    MyTaskPermissionsResponse,
)
from app.api.v1.services.task_service import TaskService
from app.api.v1.services.task_permission_service import TaskPermissionService
from app.api.v1.services.task_comment_service import TaskCommentService
from app.api.v1.services.task_commit_service import TaskCommitService
from app.api.v1.utils.pagination import paginate_query, create_paginated_response


router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ─────────────────────────────────────────────────────────────────
#  Helper dependency: admin OR employee with task-manager permission
# ─────────────────────────────────────────────────────────────────

def require_task_manager(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
) -> User:
    if not TaskPermissionService.has_task_manager_access(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Task-manager access required. Ask your admin to grant you permission.",
                "error_code": "TASK_MANAGER_ACCESS_REQUIRED",
            },
        )
    return current_user


# ─────────────────────────────────────────────────────────────────
#  Task Permissions
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/permissions/me",
    response_model=MyTaskPermissionsResponse,
    tags=["Task Permissions"],
)
async def get_my_task_permissions(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Return all task-module permissions for the logged-in user.
    Any authenticated user may call this; extend the service when new permission types are added.
    """
    items = TaskPermissionService.build_my_task_permissions(db, current_user)
    return MyTaskPermissionsResponse(permissions=items)


@router.get("/permissions", response_model=List[TaskPermissionResponse], tags=["Task Permissions"])
async def list_task_permissions(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    """List all employees who have been granted task-manager permission."""
    return TaskPermissionService.list_permissions(db, current_user.company_id)


@router.post("/permissions/grant", response_model=TaskPermissionResponse, status_code=status.HTTP_201_CREATED, tags=["Task Permissions"])
async def grant_task_permission(
    data: TaskPermissionGrant,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    """Grant task-manager permission to an employee so they can create and assign tasks."""
    return TaskPermissionService.grant(db, current_user.company_id, current_user.id, data)


@router.delete("/permissions/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Task Permissions"])
async def revoke_task_permission(
    target_user_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    """Revoke task-manager permission from a user."""
    TaskPermissionService.revoke(db, current_user.company_id, target_user_id)


# ─────────────────────────────────────────────────────────────────
#  Core Task CRUD
# ─────────────────────────────────────────────────────────────────

@router.post("/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    data: TaskCreate,
    current_user: User = Depends(require_task_manager),
    db: Session = Depends(get_database_session),
):
    """
    Create a task. Available to admins and employees who have been granted
    task-manager permission.
    """
    task = TaskService.create_task(
        db=db,
        company_id=current_user.company_id,
        creator_user_id=current_user.id,
        data=data,
    )
    task_with_relations = (
        db.query(Task)
        .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
        .filter(Task.id == task.id, Task.company_id == current_user.company_id)
        .first()
    )
    return TaskResponse.model_validate(task_with_relations)


@router.get("/my-tasks", response_model=PaginatedResponse[TaskResponse])
async def get_my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """Get all tasks assigned to the currently logged-in employee."""
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an employee",
        )

    query = db.query(Task).options(
        joinedload(Task.assigned_to_employee),
        joinedload(Task.project),
    ).filter(
        Task.company_id == current_user.company_id,
        Task.assigned_to_employee_id == current_user.employee_id,
    )

    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)

    total = query.count()
    items = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse[TaskResponse](
        data=[TaskResponse.model_validate(item) for item in items],
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.post("/query", response_model=PaginatedResponse[TaskResponse])
async def query_tasks(
    pagination_request: PaginationRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Query tasks with pagination, filtering, and sorting.
    Employees see only their assigned tasks; admins and task-managers see all.
    """
    query = db.query(Task).options(
        joinedload(Task.assigned_to_employee),
        joinedload(Task.project),
    ).filter(Task.company_id == current_user.company_id)

    # Regular employees (no task-manager permission) see only their tasks
    if current_user.role == UserRole.EMPLOYEE and not TaskPermissionService.has_task_manager_access(db, current_user):
        if not current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with an employee",
            )
        query = query.filter(Task.assigned_to_employee_id == current_user.employee_id)

    items, pagination_info = paginate_query(query, pagination_request, Task)
    return create_paginated_response(items, pagination_info, TaskResponse)


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Get full task detail including comments and git commits.
    Employees can only view tasks assigned to them (unless they have task-manager access).
    """
    from app.api.v1.models.task_comment_model import TaskComment
    from app.api.v1.models.task_commit_model import TaskCommit

    task = (
        db.query(Task)
        .options(
            joinedload(Task.assigned_to_employee),
            joinedload(Task.project),
            joinedload(Task.created_by_user),
            joinedload(Task.comments).joinedload(TaskComment.user),
            joinedload(Task.commits).joinedload(TaskCommit.added_by),
        )
        .filter(Task.id == task_id, Task.company_id == current_user.company_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Employees without task-manager access can only see their own tasks
    if current_user.role == UserRole.EMPLOYEE and not TaskPermissionService.has_task_manager_access(db, current_user):
        if task.assigned_to_employee_id != current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this task")

    return TaskDetailResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task_information(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)

    has_manager_access = TaskPermissionService.has_task_manager_access(db, current_user)

    if not has_manager_access:
        # Regular employee: can only update their own task, cannot reassign
        if task.assigned_to_employee_id != current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task")
        if data.assigned_to_employee_id is not None and data.assigned_to_employee_id != task.assigned_to_employee_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You do not have permission to reassign tasks")

    updated = TaskService.update_task(db, current_user.company_id, task_id, data, current_user.id)
    task_with_relations = (
        db.query(Task)
        .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
        .filter(Task.id == task_id, Task.company_id == current_user.company_id)
        .first()
    )
    return TaskResponse.model_validate(task_with_relations)


@router.post("/{task_id}/close", response_model=TaskResponse)
async def close_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    task = TaskService.get_task_by_id(db, current_user.company_id, task_id)

    has_manager_access = TaskPermissionService.has_task_manager_access(db, current_user)
    if not has_manager_access and task.assigned_to_employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to close this task")

    TaskService.close_task(db, current_user.company_id, task_id)
    task_with_relations = (
        db.query(Task)
        .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
        .filter(Task.id == task_id, Task.company_id == current_user.company_id)
        .first()
    )
    return TaskResponse.model_validate(task_with_relations)


# ─────────────────────────────────────────────────────────────────
#  Issue Discussion — Comments
# ─────────────────────────────────────────────────────────────────

def _assert_task_accessible(db: Session, task_id: int, current_user: User) -> Task:
    """Ensure the task exists and the current user is allowed to see it."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.company_id == current_user.company_id,
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Employees without manager access can only interact with their own tasks
    if current_user.role == UserRole.EMPLOYEE and not TaskPermissionService.has_task_manager_access(db, current_user):
        if task.assigned_to_employee_id != current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this task")

    return task


@router.get("/{task_id}/comments", response_model=List[TaskCommentResponse], tags=["Task Comments"])
async def list_task_comments(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """List all comments on a task (oldest first)."""
    _assert_task_accessible(db, task_id, current_user)
    return TaskCommentService.list_comments(db, task_id, current_user.company_id)


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED, tags=["Task Comments"])
async def add_task_comment(
    task_id: int,
    data: TaskCommentCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """Add a comment to a task. Anyone with access to the task can comment."""
    _assert_task_accessible(db, task_id, current_user)
    return TaskCommentService.add_comment(db, task_id, current_user.company_id, current_user.id, data)


@router.put("/{task_id}/comments/{comment_id}", response_model=TaskCommentResponse, tags=["Task Comments"])
async def update_task_comment(
    task_id: int,
    comment_id: int,
    data: TaskCommentUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """Edit a comment. Users can only edit their own comments; admins can edit any."""
    _assert_task_accessible(db, task_id, current_user)
    return TaskCommentService.update_comment(db, comment_id, task_id, current_user.company_id, current_user, data)


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Task Comments"])
async def delete_task_comment(
    task_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """Delete a comment. Users can only delete their own; admins can delete any."""
    _assert_task_accessible(db, task_id, current_user)
    TaskCommentService.delete_comment(db, comment_id, task_id, current_user.company_id, current_user)


# ─────────────────────────────────────────────────────────────────
#  Git Tracking — Commits & Branches
# ─────────────────────────────────────────────────────────────────

@router.get("/{task_id}/commits", response_model=List[TaskCommitResponse], tags=["Task Git"])
async def list_task_commits(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """List all commit/branch records linked to a task."""
    _assert_task_accessible(db, task_id, current_user)
    return TaskCommitService.list_commits(db, task_id, current_user.company_id)


@router.post("/{task_id}/commits", response_model=TaskCommitResponse, status_code=status.HTTP_201_CREATED, tags=["Task Git"])
async def add_task_commit(
    task_id: int,
    data: TaskCommitCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Link a commit or branch to a task.
    Any user with access to the task can add git information.
    """
    _assert_task_accessible(db, task_id, current_user)
    return TaskCommitService.add_commit(db, task_id, current_user.company_id, current_user.id, data)


@router.delete("/{task_id}/commits/{commit_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Task Git"])
async def delete_task_commit(
    task_id: int,
    commit_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """Remove a commit record. Users can only remove records they added; admins can remove any."""
    _assert_task_accessible(db, task_id, current_user)
    TaskCommitService.delete_commit(db, commit_id, task_id, current_user.company_id, current_user)
