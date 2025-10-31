"""
Schemas package for the HRMS application.
"""

from app.api.v1.schemas.company_schema import (
    CompanyBase,
    CompanyRegister,
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyRegistrationResponse,
)
from app.api.v1.schemas.department_schema import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
)
from app.api.v1.schemas.employee_schema import (
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeWithCredentials,
)
from app.api.v1.schemas.user_schema import (
    UserRoleEnum,
    UserRegister,
    UserLogin,
    PasswordChange,
    UserResponse,
    TokenResponse,
    MessageResponse,
)

__all__ = [
    # Company schemas
    "CompanyBase",
    "CompanyRegister",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    "CompanyRegistrationResponse",
    # Department schemas
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentResponse",
    # Employee schemas
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeWithCredentials",
    # User schemas
    "UserRoleEnum",
    "UserRegister",
    "UserLogin",
    "PasswordChange",
    "UserResponse",
    "TokenResponse",
    "MessageResponse",
]

