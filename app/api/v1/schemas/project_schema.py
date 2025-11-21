from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional, List, Any


class ProjectBase(BaseModel):
    """Base schema for Project"""
    name: str = Field(..., min_length=2, max_length=255, description="Project name")
    client: str = Field(..., min_length=2, max_length=255, description="Client name")
    number_of_days: int = Field(..., gt=0, description="Expected duration in days")
    target_date: date = Field(..., description="Project deadline/target date")
    project_lead_id: Optional[int] = Field(None, description="ID of the user who is the project lead")


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    client: Optional[str] = Field(None, min_length=2, max_length=255)
    number_of_days: Optional[int] = Field(None, gt=0)
    target_date: Optional[date] = None
    project_lead_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectLeadInfo(BaseModel):
    """Schema for project lead information"""
    id: int
    username: str
    full_name: str
    email: str
    
    model_config = {"from_attributes": True}


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    project_lead: Optional[ProjectLeadInfo] = None
    
    @field_validator('project_lead', mode='before')
    @classmethod
    def convert_user_to_lead_info(cls, v: Any) -> Optional[ProjectLeadInfo]:
        """Convert User object to ProjectLeadInfo"""
        if v is None:
            return None
        if isinstance(v, dict):
            return ProjectLeadInfo(**v)
        # If it's a User SQLAlchemy object, extract the fields
        if hasattr(v, 'id'):
            return ProjectLeadInfo(
                id=v.id,
                username=v.username,
                full_name=v.full_name,
                email=v.email
            )
        return v
    
    model_config = {"from_attributes": True}


class ProjectWithTasksResponse(ProjectResponse):
    """Schema for project response with task count"""
    task_count: int = 0
    completed_task_count: int = 0
    open_task_count: int = 0
    
    model_config = {"from_attributes": True}

