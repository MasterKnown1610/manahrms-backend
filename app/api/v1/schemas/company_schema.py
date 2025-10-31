from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class CompanyBase(BaseModel):
    """Base schema for Company"""
    company_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None


class CompanyRegister(BaseModel):
    """Schema for company registration with admin user"""
    # Company details
    company_name: str = Field(..., min_length=2, max_length=255, description="Company name")
    company_email: EmailStr = Field(..., description="Company email address")
    company_phone: Optional[str] = Field(None, max_length=20, description="Company phone number")
    company_address: Optional[str] = Field(None, description="Company address")
    
    # Admin user details
    admin_full_name: str = Field(..., min_length=2, max_length=255, description="Admin full name")
    admin_email: EmailStr = Field(..., description="Admin email address")
    admin_username: str = Field(..., min_length=3, max_length=50, description="Admin username")
    admin_password: str = Field(..., min_length=6, description="Admin password (min 6 characters)")


class CompanyCreate(CompanyBase):
    """Schema for creating a company"""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company"""
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Schema for company response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class CompanyRegistrationResponse(BaseModel):
    """Response after successful company registration"""
    company: CompanyResponse
    admin_username: str
    message: str = "Company registered successfully"
    
    model_config = {"from_attributes": True}

