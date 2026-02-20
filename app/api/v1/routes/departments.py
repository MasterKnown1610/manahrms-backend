from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from app.db.session import get_database_session
from app.api.v1.schemas.department_schema import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentAccessGrant,
    DepartmentAccessRevoke,
    DepartmentAccessResponse,
    DepartmentUsersAccessResponse,
    UserAccessInfo
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.models.department_model import Department
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.user_model import User
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.services.department_service import DepartmentService
from app.api.v1.services.vector_sync_service import VectorSyncService
from app.api.v1.utils.pagination import paginate_query, create_paginated_response

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("/create", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_new_department(
    department_data: DepartmentCreate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    # Check if department name already exists in company
    existing = db.query(Department).filter(
        Department.name == department_data.name,
        Department.company_id == current_user.company_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists"
        )
    
    new_department = Department(
        company_id=current_user.company_id,
        name=department_data.name,
        description=department_data.description,
        is_active=True
    )
    
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    
    # Sync to vector database
    try:
        sync_service = VectorSyncService()
        sync_service.sync_department(db, new_department.id)
    except Exception as e:
        logger.error(f"Failed to sync department {new_department.id} to vector store: {str(e)}")
        # Don't fail the main operation if vector sync fails
    
    # New department has 0 members
    dept_dict = DepartmentResponse.model_validate(new_department).model_dump()
    dept_dict['member_count'] = 0
    return DepartmentResponse(**dept_dict)


@router.post("/query", response_model=PaginatedResponse[DepartmentResponse])
async def query_departments(
    pagination_request: PaginationRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Query departments with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    Admins see all departments in their company.
    Employees see only departments they have been granted access to.
    Returns member_count (number of active employees) for each department.
    """
    # Get accessible departments query
    from app.api.v1.models.user_model import UserRole
    if current_user.role == UserRole.ADMIN:
        # Admins see all departments in company
        query = db.query(Department).filter(Department.company_id == current_user.company_id)
    else:
        # Employees see only departments they have access to
        from app.api.v1.models.department_access_model import DepartmentAccess
        query = db.query(Department).join(
            DepartmentAccess,
            Department.id == DepartmentAccess.department_id
        ).filter(
            DepartmentAccess.user_id == current_user.id,
            Department.company_id == current_user.company_id
        )
    
    # Apply pagination, filters, and sorting
    items, pagination_info = paginate_query(query, pagination_request, Department)
    
    # Get all department IDs to count members efficiently
    department_ids = [dept.id for dept in items]
    
    # Count employees per department in a single query (more efficient)
    member_counts = {}
    if department_ids:
        counts = db.query(
            Employee.department_id,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.department_id.in_(department_ids),
            Employee.company_id == current_user.company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)
        ).group_by(Employee.department_id).all()
        
        member_counts = {dept_id: count for dept_id, count in counts}
    
    # Create response with member count for each department
    department_responses = []
    for dept in items:
        member_count = member_counts.get(dept.id, 0)
        dept_dict = DepartmentResponse.model_validate(dept).model_dump()
        dept_dict['member_count'] = member_count
        department_responses.append(DepartmentResponse(**dept_dict))
    
    # Create paginated response with updated items
    # Note: PaginatedResponse expects 'data' field, not 'items'
    # Must specify generic type parameter
    return PaginatedResponse[DepartmentResponse](
        data=department_responses,
        pagination=pagination_info
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department_by_id(
    department_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific department by ID.
    Only accessible if the user has been granted access to this department.
    Admins have access to all departments in their company.
    Returns member_count (number of active employees) for this department.
    """
    # Check if user has access to this department
    has_access = DepartmentService.check_department_access(
        db=db,
        user=current_user,
        department_id=department_id
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this department"
        )
    
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.company_id == current_user.company_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Count active employees in this department (excluding soft-deleted)
    member_count = db.query(func.count(Employee.id)).filter(
        Employee.department_id == department_id,
        Employee.company_id == current_user.company_id,
        Employee.is_active == True,
        Employee.deleted_at.is_(None)
    ).scalar() or 0
    
    # Create response with member count
    dept_dict = DepartmentResponse.model_validate(department).model_dump()
    dept_dict['member_count'] = member_count
    return DepartmentResponse(**dept_dict)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department_information(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.company_id == current_user.company_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Update only provided fields
    update_data = department_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(department, field, value)
    
    db.commit()
    db.refresh(department)
    
    # Sync to vector database after update
    try:
        sync_service = VectorSyncService()
        sync_service.sync_department(db, department.id)
    except Exception as e:
        logger.error(f"Failed to sync department {department.id} to vector store after update: {str(e)}")
        # Don't fail the main operation if vector sync fails
    
    # Count active employees in this department (excluding soft-deleted)
    member_count = db.query(func.count(Employee.id)).filter(
        Employee.department_id == department_id,
        Employee.company_id == current_user.company_id,
        Employee.is_active == True,
        Employee.deleted_at.is_(None)
    ).scalar() or 0
    
    # Create response with member count
    dept_dict = DepartmentResponse.model_validate(department).model_dump()
    dept_dict['member_count'] = member_count
    return DepartmentResponse(**dept_dict)


@router.delete("/{department_id}", response_model=MessageResponse)
async def delete_department(
    department_id: int,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Delete a department permanently.
    Only admins can delete departments.
    Cannot delete if there are employees assigned to the department.
    """
    # Get department name before deletion for the response message
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.company_id == current_user.company_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    department_name = department.name
    
    # Delete the department (this will raise HTTPException if employees are assigned)
    DepartmentService.delete_department(
        db=db,
        department_id=department_id,
        company_id=current_user.company_id
    )
    
    # Sync to vector database after deletion (remove from vector store)
    try:
        sync_service = VectorSyncService()
        # Note: sync_department might fail if department is already deleted
        # We could add a delete method to VectorSyncService, but for now we'll just log
        logger.info(f"Department {department_id} deleted, should be removed from vector store")
    except Exception as e:
        logger.error(f"Failed to sync department {department_id} deletion to vector store: {str(e)}")
        # Don't fail the main operation if vector sync fails
    
    return MessageResponse(
        message=f"Department '{department_name}' has been deleted successfully"
    )


# Department Access Management Endpoints (Admin Only)

@router.post("/access/grant", response_model=DepartmentAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_department_access(
    access_data: DepartmentAccessGrant,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Grant a user access to a department.
    Only admins can grant access.
    """
    access = DepartmentService.grant_department_access(
        db=db,
        department_id=access_data.department_id,
        user_id=access_data.user_id,
        granted_by_user_id=current_user.id,
        company_id=current_user.company_id
    )
    
    return DepartmentAccessResponse.model_validate(access)


@router.post("/access/revoke", response_model=MessageResponse)
async def revoke_department_access(
    access_data: DepartmentAccessRevoke,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Revoke a user's access to a department.
    Only admins can revoke access.
    """
    DepartmentService.revoke_department_access(
        db=db,
        department_id=access_data.department_id,
        user_id=access_data.user_id,
        company_id=current_user.company_id
    )
    
    return MessageResponse(
        message="Department access has been revoked successfully"
    )


@router.get("/{department_id}/users", response_model=DepartmentUsersAccessResponse)
async def get_department_users(
    department_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Get all users who have access to a specific department.
    Only admins can view this information.
    """
    users = DepartmentService.get_department_users(
        db=db,
        department_id=department_id,
        company_id=current_user.company_id
    )
    
    # Get department name
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.company_id == current_user.company_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Convert dict list to UserAccessInfo objects
    user_access_list = [UserAccessInfo(**user_dict) for user_dict in users]
    
    return DepartmentUsersAccessResponse(
        department_id=department_id,
        department_name=department.name,
        users=user_access_list
    )


@router.get("/users/{user_id}/departments", response_model=List[DepartmentResponse])
async def get_user_departments(
    user_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Get all departments a specific user has access to.
    Only admins can view this information.
    """
    departments = DepartmentService.get_user_departments(
        db=db,
        user_id=user_id,
        company_id=current_user.company_id
    )
    
    return [DepartmentResponse.model_validate(dept) for dept in departments]

