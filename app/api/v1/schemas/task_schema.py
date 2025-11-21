from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

from app.api.v1.models.task_model import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None
    project_id: Optional[int] = Field(None, description="ID of the project this task belongs to")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None
    project_id: Optional[int] = None


class ProjectInfo(BaseModel):
    """Schema for project information in task response"""
    id: int
    name: str
    client: str
    
    model_config = {"from_attributes": True}


class TaskResponse(TaskBase):
    id: int
    company_id: int
    status: TaskStatus
    created_by_user_id: Optional[int] = None
    project: Optional[ProjectInfo] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


