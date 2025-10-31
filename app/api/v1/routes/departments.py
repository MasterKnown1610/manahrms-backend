from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.v1.schemas.department_schema import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.models.department_model import Department
from app.api.v1.dependencies import get_current_user, require_admin


router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    department_data: DepartmentCreate,
    current_user = Depends(require_admin),  # Only admins can create departments
    db: Session = Depends(get_db)
):
    """
    Create a new department (Admin only).
    
    Required fields:
    - **name**: Department name
    - **description**: Department description (optional)
    
    Returns:
    - Department information
    """
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
async def get_all_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all departments in the company.
    
    Query parameters:
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **is_active**: Filter by active status
    
    Returns:
    - List of departments
    """
    query = db.query(Department).filter(
        Department.company_id == current_user.company_id
    )
    
    if is_active is not None:
        query = query.filter(Department.is_active == is_active)
    
    departments = query.offset(skip).limit(limit).all()
    
    return [DepartmentResponse.model_validate(dept) for dept in departments]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get department by ID.
    
    Returns:
    - Department information
    """
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
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user = Depends(require_admin),  # Only admins can update departments
    db: Session = Depends(get_db)
):
    """
    Update department information (Admin only).
    
    Optional fields:
    - **name**: Department name
    - **description**: Department description
    - **is_active**: Active status
    
    Returns:
    - Updated department information
    """
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
async def delete_department(
    department_id: int,
    current_user = Depends(require_admin),  # Only admins can delete departments
    db: Session = Depends(get_db)
):
    """
    Deactivate a department (Admin only).
    
    Soft delete - sets is_active=false.
    
    Returns:
    - Success message
    """
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

