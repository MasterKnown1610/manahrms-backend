from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.api.v1.models.employee_attachment_model import AttachmentType


class EmployeeAttachmentBase(BaseModel):
    """Base schema for employee attachment"""
    attachment_type: AttachmentType
    description: Optional[str] = None


class EmployeeAttachmentCreate(EmployeeAttachmentBase):
    """Schema for creating an employee attachment (used internally)"""
    file_name: str
    file_path: str
    file_size: int
    mime_type: str


class EmployeeAttachmentResponse(EmployeeAttachmentBase):
    """Schema for employee attachment response"""
    id: int
    company_id: int
    employee_id: int
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    created_at: datetime
    updated_at: datetime
    download_url: Optional[str] = None  # Presigned URL for downloading S3 files (if applicable)
    view_url: Optional[str] = None  # Presigned URL for viewing files inline (e.g., in img tag) (if applicable)
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class EmployeeAttachmentUpload(BaseModel):
    """Schema for file upload request"""
    attachment_type: AttachmentType
    description: Optional[str] = Field(None, max_length=500)


class EmployeeAttachmentListResponse(BaseModel):
    """Response containing list of attachments"""
    attachments: list[EmployeeAttachmentResponse]
    total: int
    
    model_config = {"from_attributes": True}
