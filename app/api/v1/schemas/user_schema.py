from pydantic import BaseModel, EmailStr, Field, field_validator, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    EMPLOYEE = "employee"


# Request Schemas
class UserRegister(BaseModel):
    """Schema for user registration (deprecated - use CompanyRegister instead)"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (can include _ and -)')
        return v


class UserLogin(BaseModel):
    """Schema for user login - username field accepts either username or email"""
    username: str = Field(..., description="Username or email address")
    password: str


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Response Schemas
class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: int
    company_id: int
    email: str
    username: str
    full_name: str
    role: UserRoleEnum
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    department_permissions: Dict[str, Any] = Field(default_factory=dict)
    employee_permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions_overridden: bool = False
    employee_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    force_password_change: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

    @field_validator(
        "permissions",
        "department_permissions",
        "employee_permissions",
        mode="before",
    )
    @classmethod
    def empty_dict_if_none(cls, value):
        return value if value is not None else {}


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr = Field(..., description="Company admin email address")


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password using a token"""
    token: str = Field(..., description="Password reset token received via email")
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


