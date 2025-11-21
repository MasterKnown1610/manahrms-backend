from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

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
from app.api.v1.models.department_model import Department
from app.api.v1.models.user_model import User
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.services.department_service import DepartmentService


router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
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
    
    return DepartmentResponse.model_validate(new_department)


@router.get("/", response_model=List[DepartmentResponse])
async def get_all_company_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all departments the current user has access to.
    Admins see all departments in their company.
    Employees see only departments they have been granted access to.
    """
    departments = DepartmentService.get_accessible_departments(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
        is_active=is_active
    )
    
    return [DepartmentResponse.model_validate(dept) for dept in departments]


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
    
    return DepartmentResponse.model_validate(department)


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
    
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}", response_model=MessageResponse)
async def deactivate_department(
    department_id: int,
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
    
    department.is_active = False
    db.commit()
    
    return MessageResponse(
        message=f"Department '{department.name}' has been deactivated successfully"
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

