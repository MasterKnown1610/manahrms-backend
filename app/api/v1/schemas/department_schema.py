from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DepartmentBase(BaseModel):
    """Base schema for Department"""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    """Schema for creating a department"""
    pass


class DepartmentUpdate(BaseModel):
    """Schema for updating a department"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    """Schema for department response"""
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

