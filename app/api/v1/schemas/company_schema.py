from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum


class CompanyTypeEnum(str, Enum):
    """Company type enumeration for dropdown"""
    SOLO_PROPRIETOR = "Solo Proprietor"
    ORGANIZATION = "Organization"
    PRIVATE_LIMITED = "Private Limited"
    LLP = "LLP"
    PARTNERSHIP = "Partnership"
    PUBLIC_LIMITED = "Public Limited"
    OTHER = "Other"


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
    company_type: CompanyTypeEnum = Field(..., description="Company type (dropdown selection)")
    company_type_other: Optional[str] = Field(None, max_length=255, description="Custom company type (required if company_type is 'Other')")
    company_gst_number: Optional[str] = Field(None, max_length=50, description="Company GST number (optional)")
    company_pan_number: str = Field(..., max_length=50, description="Company PAN number (required)")
    
    # Admin user details
    admin_full_name: str = Field(..., min_length=2, max_length=255, description="Admin full name")
    admin_email: EmailStr = Field(..., description="Admin email address")
    admin_username: str = Field(..., min_length=3, max_length=50, description="Admin username")
    company_password: str = Field(..., min_length=6, description="Company password (min 6 characters)")
    
    @model_validator(mode='after')
    def validate_company_type_other(self):
        """Validate that company_type_other is provided when company_type is 'Other'"""
        if self.company_type == CompanyTypeEnum.OTHER:
            if not self.company_type_other or not self.company_type_other.strip():
                raise ValueError("company_type_other is required when company_type is 'Other'")
        return self


class CompanyCreate(CompanyBase):
    """Schema for creating a company"""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company"""
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    company_type: Optional[CompanyTypeEnum] = None
    company_type_other: Optional[str] = Field(None, max_length=255)
    gst_number: Optional[str] = Field(None, max_length=50)
    pan_number: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Schema for company response"""
    id: int
    company_code: str
    company_type: str
    company_type_other: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: str
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

