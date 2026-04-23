from typing import Optional, List
from datetime import datetime, time
from pydantic import BaseModel, Field


class ShiftCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    start_time: time
    end_time: time
    shift_days: Optional[List[str]] = None  # ["monday","tuesday",...] or ["all"]


class ShiftUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    shift_days: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ShiftResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: Optional[str] = None
    start_time: time
    end_time: time
    shift_days: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftAssignmentCreate(BaseModel):
    shift_id: int
    employee_id: int
    effective_from: datetime
    effective_to: Optional[datetime] = None


class ShiftAssignmentResponse(BaseModel):
    id: int
    company_id: int
    shift_id: int
    employee_id: int
    effective_from: datetime
    effective_to: Optional[datetime] = None
    assigned_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
