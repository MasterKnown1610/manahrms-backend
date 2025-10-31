from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
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
    """Schema for user login"""
    username: str
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
    is_active: bool
    is_superuser: bool
    force_password_change: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


