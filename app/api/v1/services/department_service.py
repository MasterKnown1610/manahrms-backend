from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from app.api.v1.models.department_model import Department
from app.api.v1.models.department_access_model import DepartmentAccess
from app.api.v1.models.user_model import User, UserRole


class DepartmentService:
    """
    Service class for department access management operations.
    """

    @staticmethod
    def check_department_access(
        db: Session,
        user: User,
        department_id: int
    ) -> bool:
        """
        Check if a user has access to a specific department.
        Admins always have access. Employees need explicit access grant.
        """
        # Admins always have access to all departments in their company
        if user.role == UserRole.ADMIN:
            # Verify department belongs to user's company
            department = db.query(Department).filter(
                Department.id == department_id,
                Department.company_id == user.company_id
            ).first()
            return department is not None
        
        # For employees, check if they have explicit access
        access = db.query(DepartmentAccess).filter(
            and_(
                DepartmentAccess.user_id == user.id,
                DepartmentAccess.department_id == department_id,
                DepartmentAccess.is_active == True
            )
        ).first()
        
        if access:
            # Verify department belongs to user's company and is active
            department = db.query(Department).filter(
                Department.id == department_id,
                Department.company_id == user.company_id,
                Department.is_active == True
            ).first()
            return department is not None
        
        return False

    @staticmethod
    def get_accessible_departments(
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Department]:
        """
        Get all departments a user has access to.
        Admins see all departments in their company.
        Employees see only departments they have been granted access to.
        """
        if user.role == UserRole.ADMIN:
            # Admins see all departments in their company
            query = db.query(Department).filter(
                Department.company_id == user.company_id
            )
            if is_active is not None:
                query = query.filter(Department.is_active == is_active)
        else:
            # Employees see only departments they have access to
            query = db.query(Department).join(
                DepartmentAccess,
                and_(
                    DepartmentAccess.department_id == Department.id,
                    DepartmentAccess.user_id == user.id,
                    DepartmentAccess.is_active == True
                )
            ).filter(
                Department.company_id == user.company_id
            )
            if is_active is not None:
                query = query.filter(Department.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def grant_department_access(
        db: Session,
        department_id: int,
        user_id: int,
        granted_by_user_id: int,
        company_id: int
    ) -> DepartmentAccess:
        """
        Grant a user access to a department.
        Only admins can grant access.
        """
        # Verify department exists and belongs to company
        department = db.query(Department).filter(
            Department.id == department_id,
            Department.company_id == company_id
        ).first()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Verify user exists and belongs to company
        user = db.query(User).filter(
            User.id == user_id,
            User.company_id == company_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if access already exists
        existing_access = db.query(DepartmentAccess).filter(
            and_(
                DepartmentAccess.department_id == department_id,
                DepartmentAccess.user_id == user_id
            )
        ).first()
        
        if existing_access:
            # Reactivate if it was deactivated
            if not existing_access.is_active:
                existing_access.is_active = True
                existing_access.granted_by = granted_by_user_id
                db.commit()
                db.refresh(existing_access)
                return existing_access
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already has access to this department"
                )
        
        # Create new access record
        access = DepartmentAccess(
            department_id=department_id,
            user_id=user_id,
            granted_by=granted_by_user_id,
            is_active=True
        )
        
        db.add(access)
        db.commit()
        db.refresh(access)
        
        return access

    @staticmethod
    def revoke_department_access(
        db: Session,
        department_id: int,
        user_id: int,
        company_id: int
    ) -> None:
        """
        Revoke a user's access to a department.
        Only admins can revoke access.
        """
        # Verify department exists and belongs to company
        department = db.query(Department).filter(
            Department.id == department_id,
            Department.company_id == company_id
        ).first()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Find and deactivate access
        access = db.query(DepartmentAccess).filter(
            and_(
                DepartmentAccess.department_id == department_id,
                DepartmentAccess.user_id == user_id
            )
        ).first()
        
        if not access:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access record not found"
            )
        
        if not access.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access is already revoked"
            )
        
        access.is_active = False
        db.commit()

    @staticmethod
    def get_department_users(
        db: Session,
        department_id: int,
        company_id: int
    ) -> List[dict]:
        """
        Get all users who have access to a specific department.
        """
        # Verify department exists and belongs to company
        department = db.query(Department).filter(
            Department.id == department_id,
            Department.company_id == company_id
        ).first()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Get all active access records for this department
        access_records = db.query(DepartmentAccess).join(
            User,
            DepartmentAccess.user_id == User.id
        ).filter(
            and_(
                DepartmentAccess.department_id == department_id,
                DepartmentAccess.is_active == True,
                User.company_id == company_id
            )
        ).all()
        
        result = []
        for access in access_records:
            result.append({
                "user_id": access.user_id,
                "username": access.user.username,
                "full_name": access.user.full_name,
                "email": access.user.email,
                "role": access.user.role.value,
                "granted_at": access.created_at,
                "granted_by": access.granted_by
            })
        
        return result

    @staticmethod
    def get_user_departments(
        db: Session,
        user_id: int,
        company_id: int
    ) -> List[Department]:
        """
        Get all departments a specific user has access to.
        """
        # Verify user exists and belongs to company
        user = db.query(User).filter(
            User.id == user_id,
            User.company_id == company_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.role == UserRole.ADMIN:
            # Admins have access to all departments
            return db.query(Department).filter(
                Department.company_id == company_id
            ).all()
        
        # Get departments user has access to
        departments = db.query(Department).join(
            DepartmentAccess,
            and_(
                DepartmentAccess.department_id == Department.id,
                DepartmentAccess.user_id == user_id,
                DepartmentAccess.is_active == True
            )
        ).filter(
            Department.company_id == company_id
        ).all()
        
        return departments

