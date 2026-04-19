from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

from app.api.v1.models.task_model import TaskStatus, TaskPriority


# ─────────────────────────────────────────────
#  Nested info schemas
# ─────────────────────────────────────────────

class ProjectInfo(BaseModel):
    id: int
    name: str
    client: str

    model_config = {"from_attributes": True}


class EmployeeInfo(BaseModel):
    id: int
    employee_code: str
    full_name: str

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    id: int
    username: str
    full_name: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  Task CRUD schemas
# ─────────────────────────────────────────────

class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None
    project_id: Optional[int] = Field(None, description="ID of the project this task belongs to")
    branch: Optional[str] = Field(None, max_length=255, description="Primary branch for this task (e.g. feature/task-42)")


class TaskCreate(TaskBase):
    parent_task_id: Optional[int] = Field(
        None,
        description="ID of the parent task. Set this to create a subtask (e.g. 1.1 under task 1).",
    )


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None
    project_id: Optional[int] = None
    branch: Optional[str] = Field(None, max_length=255)
    parent_task_id: Optional[int] = Field(None, description="Move this task under a different parent (or null to make it top-level)")
    position: Optional[int] = Field(None, ge=0, description="Display order within the same parent (0-based)")


class TaskResponse(TaskBase):
    id: int
    company_id: int
    status: TaskStatus
    parent_task_id: Optional[int] = None
    position: int = 0
    created_by_user_id: Optional[int] = None
    project: Optional[ProjectInfo] = None
    assigned_to_employee: Optional[EmployeeInfo] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  Hierarchical / Tree schemas
# ─────────────────────────────────────────────

class TaskTreeNode(BaseModel):
    """
    One node in a task hierarchy tree.
    task_number is computed on-the-fly (e.g. "1", "1.2", "1.2.3").
    subtasks contains direct children, themselves with their own subtasks.
    """
    id: int
    task_number: str = Field(..., description='Computed display number e.g. "1", "1.2", "2.1.3"')
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date] = None
    parent_task_id: Optional[int] = None
    position: int = 0
    assigned_to_employee: Optional[EmployeeInfo] = None
    project: Optional[ProjectInfo] = None
    created_at: datetime
    updated_at: datetime
    subtasks: List[TaskTreeNode] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# Required to resolve the forward reference in subtasks
TaskTreeNode.model_rebuild()


class TaskTreeResponse(BaseModel):
    """Full tree rooted at a parent task (or top-level tasks list)."""
    tasks: List[TaskTreeNode]
    total_root_tasks: int
    total_tasks: int  # includes all nested subtasks


class SubtaskCreate(BaseModel):
    """Body for POST /tasks/{task_id}/subtasks — parent is the path param."""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None
    project_id: Optional[int] = None
    branch: Optional[str] = Field(None, max_length=255)


# ─────────────────────────────────────────────
#  Task Comments (Issue Discussion)
# ─────────────────────────────────────────────

class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Comment content")


class TaskCommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class TaskCommentResponse(BaseModel):
    id: int
    task_id: int
    company_id: int
    user_id: Optional[int] = None
    content: str
    user: Optional[UserInfo] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  Task Commits / Git Info
# ─────────────────────────────────────────────

class TaskCommitCreate(BaseModel):
    branch: Optional[str] = Field(None, max_length=255, description="Branch name (e.g. feature/task-42)")
    commit_hash: Optional[str] = Field(None, max_length=100, description="Full or short commit hash")
    commit_message: Optional[str] = Field(None, description="Commit message")
    author_name: Optional[str] = Field(None, max_length=255, description="Commit author name")
    commit_url: Optional[str] = Field(None, max_length=500, description="Link to commit on GitHub/GitLab etc.")
    committed_at: Optional[datetime] = Field(None, description="When the commit was made")


class TaskCommitResponse(BaseModel):
    id: int
    task_id: int
    company_id: int
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    author_name: Optional[str] = None
    commit_url: Optional[str] = None
    committed_at: Optional[datetime] = None
    added_by_user_id: Optional[int] = None
    added_by: Optional[UserInfo] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  Task Permissions
# ─────────────────────────────────────────────

class TaskPermissionGrant(BaseModel):
    user_id: int = Field(..., description="ID of the user to grant task-manager access")


class TaskPermissionResponse(BaseModel):
    id: int
    company_id: int
    user_id: int
    granted_by_user_id: Optional[int] = None
    user: Optional[UserInfo] = None
    granted_by: Optional[UserInfo] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskModulePermissionCode(str, Enum):
    """Stable codes for task-module capabilities; extend as new grants are added."""

    TASK_MANAGER = "task_manager"


class MyTaskPermissionItem(BaseModel):
    """One permission the authenticated user has within the task module."""

    code: TaskModulePermissionCode = Field(..., description="Permission identifier")
    granted_at: Optional[datetime] = Field(
        None,
        description="When this grant was recorded; null if implied by role (e.g. admin)",
    )


class MyTaskPermissionsResponse(BaseModel):
    """All task-module permissions for the current user; safe for any authenticated employee."""

    permissions: List[MyTaskPermissionItem]


# ─────────────────────────────────────────────
#  Rich single-task detail (GET /tasks/{id})
# ─────────────────────────────────────────────

class TaskDetailResponse(BaseModel):
    """Full task detail including comments, git commits, and direct subtasks."""
    id: int
    company_id: int
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[date] = None
    branch: Optional[str] = None
    parent_task_id: Optional[int] = None
    position: int = 0
    assigned_to_employee_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    project_id: Optional[int] = None
    project: Optional[ProjectInfo] = None
    assigned_to_employee: Optional[EmployeeInfo] = None
    created_by_user: Optional[UserInfo] = None
    comments: List[TaskCommentResponse] = []
    commits: List[TaskCommitResponse] = []
    subtasks: List[TaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
