from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.v1.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeWithCredentials
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.services.employee_service import EmployeeService
from app.api.v1.dependencies import get_current_user, require_admin


router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("/", response_model=EmployeeWithCredentials, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user = Depends(require_admin),  # Only admins can create employees
    db: Session = Depends(get_db)
):
    """
    Create a new employee (Admin only).
    
    **Only company admins can access this endpoint.**
    
    Required fields:
    - **employee_code**: Unique employee code/ID
    - **first_name**: Employee's first name
    - **last_name**: Employee's last name
    - **email**: Employee's email address (must be unique)
    - **hire_date**: Date of hire
    - **initial_password**: Temporary password for employee's first login
    
    Optional fields:
    - **phone**: Phone number
    - **date_of_birth**: Date of birth
    - **position**: Job position/title
    - **department_id**: Department ID
    - **salary**: Employee salary
    
    Returns:
    - Employee information
    - Generated username for employee login
    - Temporary password (same as initial_password provided)
    - Success message
    
    Flow after creation:
    1. Employee receives credentials (via email/manual communication)
    2. Employee logs in with username and temporary password
    3. System prompts employee to change password
    4. Employee can access employee portal
    
    Example:
    ```json
    {
      "employee_code": "EMP001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1234567890",
      "position": "Software Engineer",
      "hire_date": "2025-01-15",
      "initial_password": "TempPass123",
      "department_id": 1,
      "salary": 75000.00
    }
    ```
    
    Notes:
    - Username is auto-generated from employee_code
    - Employee account is set to force password change on first login
    - Employee is automatically linked to admin's company
    """
    employee, user, temp_password = EmployeeService.create_employee(
        db, 
        employee_data, 
        current_user.company_id
    )
    
    return EmployeeWithCredentials(
        employee=EmployeeResponse.model_validate(employee),
        username=user.username,
        temp_password=temp_password,
        message="Employee created successfully. Please share credentials with the employee."
    )


@router.get("/", response_model=List[EmployeeResponse])
async def get_all_employees(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all employees in the company.
    
    **Both admins and employees can access this endpoint.**
    - Admins see all employees in their company
    - Employees see all employees in their company (read-only)
    
    Query parameters:
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum records to return (default: 100, max: 1000)
    - **is_active**: Filter by active status (true/false/null for all)
    
    Returns:
    - List of employee records
    
    Example:
    ```
    GET /api/v1/employees?skip=0&limit=50&is_active=true
    ```
    """
    employees = EmployeeService.get_all_employees(
        db,
        current_user.company_id,
        skip=skip,
        limit=limit,
        is_active=is_active
    )
    
    return [EmployeeResponse.model_validate(emp) for emp in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get employee by ID.
    
    **Both admins and employees can access this endpoint.**
    - Returns employee details if they belong to the same company
    
    Path parameters:
    - **employee_id**: Employee ID
    
    Returns:
    - Employee information
    
    Example:
    ```
    GET /api/v1/employees/1
    ```
    """
    employee = EmployeeService.get_employee_by_id(
        db,
        employee_id,
        current_user.company_id
    )
    
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user = Depends(require_admin),  # Only admins can update employees
    db: Session = Depends(get_db)
):
    """
    Update employee information (Admin only).
    
    **Only company admins can access this endpoint.**
    
    Path parameters:
    - **employee_id**: Employee ID to update
    
    Optional fields (update only what you provide):
    - **first_name**: Employee's first name
    - **last_name**: Employee's last name
    - **email**: Employee's email address
    - **phone**: Phone number
    - **date_of_birth**: Date of birth
    - **position**: Job position/title
    - **department_id**: Department ID
    - **salary**: Employee salary
    - **is_active**: Active status
    
    Returns:
    - Updated employee information
    
    Example:
    ```json
    {
      "position": "Senior Software Engineer",
      "salary": 85000.00,
      "department_id": 2
    }
    ```
    
    Notes:
    - Only provided fields will be updated
    - Cannot change employee_code or hire_date
    - Setting is_active=false deactivates employee and their user account
    """
    employee = EmployeeService.update_employee(
        db,
        employee_id,
        current_user.company_id,
        employee_data
    )
    
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def delete_employee(
    employee_id: int,
    current_user = Depends(require_admin),  # Only admins can delete employees
    db: Session = Depends(get_db)
):
    """
    Deactivate an employee (Admin only).
    
    **Only company admins can access this endpoint.**
    
    This performs a soft delete by setting is_active=false.
    - Employee record is preserved for historical data
    - Employee cannot login after deactivation
    - Admin can reactivate later if needed
    
    Path parameters:
    - **employee_id**: Employee ID to deactivate
    
    Returns:
    - Success message
    
    Example:
    ```
    DELETE /api/v1/employees/1
    ```
    
    Notes:
    - Employee user account is also deactivated
    - Employee data remains in database for records
    - Use PUT endpoint with is_active=true to reactivate
    """
    EmployeeService.delete_employee(
        db,
        employee_id,
        current_user.company_id
    )
    
    return MessageResponse(
        message=f"Employee {employee_id} has been deactivated successfully"
    )

