from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr
from app.api.v1.models.lead_model import ProjectStatus


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, max_length=20)
    requirement_description: Optional[str] = None
    project_name: Optional[str] = Field(None, max_length=200)
    project_description: Optional[str] = None
    requirements: Optional[str] = None
    quoted_amount: Optional[Decimal] = Field(None, ge=0, description="Quoted amount — amount we told the client")
    confirmed_amount: Optional[Decimal] = Field(None, ge=0, description="Confirmed amount — amount the client agreed to")
    project_status: ProjectStatus = ProjectStatus.NEW


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, max_length=20)
    requirement_description: Optional[str] = None
    project_name: Optional[str] = Field(None, max_length=200)
    project_description: Optional[str] = None
    requirements: Optional[str] = None
    quoted_amount: Optional[Decimal] = Field(None, ge=0, description="Quoted amount — amount we told the client")
    confirmed_amount: Optional[Decimal] = Field(None, ge=0, description="Confirmed amount — amount the client agreed to")
    project_status: Optional[ProjectStatus] = None


class LeadResponse(BaseModel):
    id: int
    company_id: int
    name: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    requirement_description: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    requirements: Optional[str] = None
    quoted_amount: Optional[Decimal] = None
    confirmed_amount: Optional[Decimal] = None
    project_status: ProjectStatus
    source: Optional[str] = "manual"
    exotel_call_sid: Optional[str] = None
    call_recording_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
