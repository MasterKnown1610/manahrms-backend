from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


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


# Department Access Management Schemas
class DepartmentAccessGrant(BaseModel):
    """Schema for granting department access to a user"""
    user_id: int = Field(..., description="ID of the user to grant access to")
    department_id: int = Field(..., description="ID of the department to grant access to")


class DepartmentAccessRevoke(BaseModel):
    """Schema for revoking department access from a user"""
    user_id: int = Field(..., description="ID of the user to revoke access from")
    department_id: int = Field(..., description="ID of the department to revoke access from")


class DepartmentAccessResponse(BaseModel):
    """Schema for department access response"""
    id: int
    department_id: int
    user_id: int
    granted_by: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class UserDepartmentAccessResponse(BaseModel):
    """Schema for listing all departments a user has access to"""
    user_id: int
    user_name: str
    departments: List['DepartmentResponse']
    
    model_config = {"from_attributes": True}


class UserAccessInfo(BaseModel):
    """Schema for user access information"""
    user_id: int
    username: str
    full_name: str
    email: str
    role: str
    granted_at: datetime
    granted_by: Optional[int] = None


class DepartmentUsersAccessResponse(BaseModel):
    """Schema for listing all users who have access to a department"""
    department_id: int
    department_name: str
    users: List[UserAccessInfo]
    
    model_config = {"from_attributes": True}

