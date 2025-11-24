from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_database_session
from app.api.v1.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeWithCredentials
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.services.employee_service import EmployeeService
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.utils.pagination import paginate_query, create_paginated_response
from app.api.v1.models.employee_model import Employee


router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("/create", response_model=EmployeeWithCredentials, status_code=status.HTTP_201_CREATED)
async def create_new_employee(
    employee_data: EmployeeCreate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    employee, user, temp_password = EmployeeService.create_employee_with_credentials(
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


@router.post("/query", response_model=PaginatedResponse[EmployeeResponse])
async def query_employees(
    pagination_request: PaginationRequest,
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Query employees with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    """
    # Build base query - exclude soft-deleted employees
    query = db.query(Employee).filter(
        Employee.company_id == current_user.company_id,
        Employee.deleted_at.is_(None)
    )
    
    # Apply pagination, filters, and sorting
    items, pagination_info = paginate_query(query, pagination_request, Employee)
    
    # Create paginated response
    return create_paginated_response(items, pagination_info, EmployeeResponse)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee_by_id(
    employee_id: int,
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    employee = EmployeeService.get_employee_by_id(
        db,
        employee_id,
        current_user.company_id
    )
    
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee_information(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    employee = EmployeeService.update_employee(
        db,
        employee_id,
        current_user.company_id,
        employee_data
    )
    
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def deactivate_employee(
    employee_id: int,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    EmployeeService.delete_employee(
        db,
        employee_id,
        current_user.company_id
    )
    
    return MessageResponse(
        message=f"Employee {employee_id} has been deleted successfully. The email can now be reused in another company."
    )

