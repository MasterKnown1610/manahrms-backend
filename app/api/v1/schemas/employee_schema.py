from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional, Dict, Any
from decimal import Decimal
from app.api.v1.models.employee_model import Gender
from app.api.v1.schemas.role_schema import ModulePermission


class EmployeeBase(BaseModel):
    """Base schema for Employee"""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    position: Optional[str] = Field(None, max_length=255)
    department_id: Optional[int] = None
    salary: Optional[Decimal] = None
    address: Optional[str] = Field(None, description="Employee address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    pin_code: Optional[str] = Field(None, max_length=10, description="PIN/ZIP code")
    notes: Optional[str] = Field(None, description="Additional notes about the employee")


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
    gender: Optional[Gender] = None
    position: Optional[str] = Field(None, max_length=255)
    department_id: Optional[int] = None
    salary: Optional[Decimal] = None
    address: Optional[str] = Field(None, description="Employee address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    pin_code: Optional[str] = Field(None, max_length=10, description="PIN/ZIP code")
    notes: Optional[str] = Field(None, description="Additional notes about the employee")
    is_active: Optional[bool] = None
    initial_password: Optional[str] = Field(
        None,
        min_length=6,
        description="Reset the employee's login password",
    )


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
    department_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    department_permissions: Dict[str, Any] = Field(default_factory=dict)
    employee_permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions_overridden: bool = False
    
    model_config = {"from_attributes": True}


class EmployeePermissionsUpdate(BaseModel):
    """
    Assign a role and/or set extra permissions for this employee.

    - role_id only → follow live Role Management permissions
    - employee_permissions → extras on top of department/role (additive)
    - permissions → same as extras (or a full matrix; extras are extracted vs role)
    - inherit_from_role=true → clear extras, department/role only
    """
    role_id: Optional[int] = None
    employee_permissions: Optional[Dict[str, ModulePermission]] = None
    permissions: Optional[Dict[str, ModulePermission]] = None
    inherit_from_role: bool = False


class EmployeePermissionsResponse(BaseModel):
    employee_id: int
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    department_permissions: Dict[str, Any] = Field(default_factory=dict)
    employee_permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    permissions_overridden: bool = False
    message: Optional[str] = None


class EmployeeWithCredentials(BaseModel):
    """Response after creating an employee with login credentials"""
    employee: EmployeeResponse
    username: str
    temp_password: str
    message: str = "Employee created successfully. Credentials sent to employee email."
    
    model_config = {"from_attributes": True}


class EmployeeDropdownResponse(BaseModel):
    """Simplified schema for employee dropdown lists"""
    id: int
    employee_code: str
    full_name: str
    
    model_config = {"from_attributes": True}

