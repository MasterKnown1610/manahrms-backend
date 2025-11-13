from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional
from decimal import Decimal


class EmployeeBase(BaseModel):
    """Base schema for Employee"""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    position: Optional[str] = Field(None, max_length=255)
    department_id: Optional[int] = None
    salary: Optional[Decimal] = None


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee"""
    hire_date: date
    initial_password: str = Field(..., min_length=6, description="Initial password for employee login")
    employee_code: Optional[str] = Field(None, min_length=3, max_length=50, description="Optional employee code (auto-generated if not provided)")


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    position: Optional[str] = Field(None, max_length=255)
    department_id: Optional[int] = None
    salary: Optional[Decimal] = None
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Schema for employee response"""
    id: int
    company_id: int
    employee_code: str
    hire_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed field
    full_name: Optional[str] = None
    
    model_config = {"from_attributes": True}


class EmployeeWithCredentials(BaseModel):
    """Response after creating an employee with login credentials"""
    employee: EmployeeResponse
    username: str
    temp_password: str
    message: str = "Employee created successfully. Credentials sent to employee email."
    
    model_config = {"from_attributes": True}

