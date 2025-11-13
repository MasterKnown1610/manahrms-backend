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


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    assigned_to_employee_id: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    company_id: int
    status: TaskStatus
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


