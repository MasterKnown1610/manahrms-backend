from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import date, datetime
import logging

from app.api.v1.models.employee_model import Employee
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.department_model import Department
from app.api.v1.models.role_model import Role
from app.api.v1.models.task_model import Task
from app.api.v1.models.employee_attachment_model import EmployeeAttachment, AttachmentType
from app.api.v1.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeePermissionsUpdate,
    EmployeePermissionsResponse,
    EmployeeResponse,
)
from app.core.security import hash_password_for_storage
from app.api.v1.services.vector_sync_service import VectorSyncService
from app.api.v1.utils.file_upload import save_uploaded_file, delete_file

logger = logging.getLogger(__name__)


def generate_unique_employee_code_for_company(db: Session, company_id: int) -> str:
    last_employee = (
        db.query(Employee)
        .filter(
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)  # Only consider non-deleted employees
        )
        .order_by(Employee.id.desc())
        .first()
    )
    
    if last_employee and last_employee.employee_code:
        try:
            if last_employee.employee_code.startswith("EMP"):
                last_num = int(last_employee.employee_code.replace("EMP", ""))
                new_num = last_num + 1
            else:
                new_num = 1
        except (ValueError, AttributeError):
            new_num = 1
    else:
        new_num = 1
    
    return f"EMP{new_num:08d}"


class EmployeeService:
    
    @staticmethod
    def create_employee_with_credentials(db: Session, employee_data: EmployeeCreate, company_id: int) -> tuple[Employee, User, str]:
        if employee_data.employee_code:
            employee_code = employee_data.employee_code
            existing_code = db.query(Employee).filter(
                Employee.employee_code == employee_code
            ).first()
            if existing_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee code already exists"
                )
        else:
            employee_code = generate_unique_employee_code_for_company(db, company_id)
            max_attempts = 10
            attempt = 0
            while db.query(Employee).filter(Employee.employee_code == employee_code).first() and attempt < max_attempts:
                try:
                    num = int(employee_code.replace("EMP", ""))
                    num += 1
                    employee_code = f"EMP{num:08d}"
                except ValueError:
                    employee_code = generate_unique_employee_code_for_company(db, company_id)
                attempt += 1
        
        # Check if email already exists for this company (excluding soft-deleted employees)
        existing_email = db.query(Employee).filter(
            Employee.email == employee_data.email,
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)  # Only check non-deleted employees
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee email already registered in this company"
            )
        
        if employee_data.department_id:
            department = db.query(Department).filter(
                Department.id == employee_data.department_id,
                Department.company_id == company_id
            ).first()
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Department not found"
                )
        
        try:
            new_employee = Employee(
                company_id=company_id,
                employee_code=employee_code,
                first_name=employee_data.first_name,
                last_name=employee_data.last_name,
                email=employee_data.email,
                phone=employee_data.phone,
                date_of_birth=employee_data.date_of_birth,
                gender=employee_data.gender,
                position=employee_data.position,
                hire_date=employee_data.hire_date,
                salary=employee_data.salary,
                department_id=employee_data.department_id,
                address=employee_data.address,
                city=employee_data.city,
                pin_code=employee_data.pin_code,
                notes=employee_data.notes,
                is_active=True
            )
            db.add(new_employee)
            db.flush()
            
            username = employee_code.lower().replace(" ", "_")
            
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                username = f"{username}_{new_employee.id}"
            
            hashed_password = hash_password_for_storage(employee_data.initial_password)
            
            employee_user = User(
                company_id=company_id,
                email=employee_data.email,
                username=username,
                full_name=f"{employee_data.first_name} {employee_data.last_name}",
                hashed_password=hashed_password,
                role=UserRole.EMPLOYEE,
                employee_id=new_employee.id,
                permissions=None,
                is_active=True,
                is_superuser=False,
                force_password_change=True
            )
            db.add(employee_user)
            
            db.commit()
            db.refresh(new_employee)
            db.refresh(employee_user)
            
            # Sync to vector database
            try:
                sync_service = VectorSyncService()
                sync_service.sync_employee(db, new_employee.id)
            except Exception as e:
                logger.error(f"Failed to sync employee {new_employee.id} to vector store: {str(e)}")
                # Don't fail the main operation if vector sync fails
            
            return new_employee, employee_user, employee_data.initial_password
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create employee: {str(e)}"
            )
    
    @staticmethod
    def get_employee_by_id(db: Session, employee_id: int, company_id: int) -> Employee:
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)  # Exclude soft-deleted employees
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        return employee

    ACTIONS = ("view", "create", "edit", "delete")

    @staticmethod
    def _permissions_to_dict(permissions) -> dict:
        if not permissions:
            return {}
        result = {}
        for module, perms in permissions.items():
            if hasattr(perms, "model_dump"):
                result[module] = perms.model_dump()
            elif isinstance(perms, dict):
                result[module] = perms
            else:
                result[module] = dict(perms)
        return result

    @staticmethod
    def _normalize_module(perms: dict) -> dict:
        return {
            action: bool((perms or {}).get(action))
            for action in EmployeeService.ACTIONS
        }

    @staticmethod
    def _merge_permissions(department: dict, extras: dict) -> dict:
        """OR-merge: employee extras add on top of live department/role permissions."""
        merged = {}
        modules = set((department or {}).keys()) | set((extras or {}).keys())
        for module in modules:
            dept_mod = EmployeeService._normalize_module((department or {}).get(module) or {})
            extra_mod = EmployeeService._normalize_module((extras or {}).get(module) or {})
            merged[module] = {
                action: dept_mod[action] or extra_mod[action]
                for action in EmployeeService.ACTIONS
            }
        return merged

    @staticmethod
    def _extras_only(incoming: dict, department: dict) -> dict:
        """Keep only flags that are extra vs the live department/role template."""
        extras = {}
        incoming = incoming or {}
        department = department or {}
        for module, perms in incoming.items():
            extra_mod = {}
            dept_mod = department.get(module) or {}
            for action in EmployeeService.ACTIONS:
                if bool((perms or {}).get(action)) and not bool(dept_mod.get(action)):
                    extra_mod[action] = True
            if extra_mod:
                extras[module] = extra_mod
        return extras

    @staticmethod
    def _department_role(db: Session, employee: Employee) -> Optional[Role]:
        """Role for employee's department. Prefer assigned role; else sole department role."""
        user = employee.user
        if user and user.custom_role_id and user.custom_role:
            same_company = user.custom_role.company_id == employee.company_id
            same_dept = (
                user.custom_role.department_id is None
                or user.custom_role.department_id == employee.department_id
            )
            if same_company and same_dept:
                return user.custom_role

        if not employee.department_id:
            return None

        dept_roles = (
            db.query(Role)
            .filter(
                Role.company_id == employee.company_id,
                Role.department_id == employee.department_id,
            )
            .order_by(Role.id.asc())
            .all()
        )
        if len(dept_roles) == 1:
            return dept_roles[0]
        if user and user.custom_role_id:
            for role in dept_roles:
                if role.id == user.custom_role_id:
                    return role
        return None

    @staticmethod
    def resolve_employee_access(
        db: Session, employee: Employee
    ) -> dict:
        """
        Department/role permissions stay live from Role Management.
        user.permissions holds extras only; effective = OR-merge of both.
        """
        user = employee.user
        role = EmployeeService._department_role(db, employee)
        department_permissions = dict(role.permissions or {}) if role else {}
        extras = dict(user.permissions) if user and user.permissions else {}
        extras = EmployeeService._extras_only(extras, department_permissions)
        effective = EmployeeService._merge_permissions(department_permissions, extras)

        role_id = None
        role_name = None
        if role:
            role_id = role.id
            role_name = role.name
        elif user and user.custom_role_id:
            role_id = user.custom_role_id
            role_name = user.custom_role.name if user.custom_role else None

        return {
            "role_id": role_id,
            "role_name": role_name,
            "department_permissions": department_permissions,
            "employee_permissions": extras,
            "permissions": effective,
            "permissions_overridden": bool(extras),
        }

    @staticmethod
    def _permissions_response(
        db: Session, employee: Employee
    ) -> EmployeePermissionsResponse:
        access = EmployeeService.resolve_employee_access(db, employee)
        return EmployeePermissionsResponse(
            employee_id=employee.id,
            department_id=employee.department_id,
            department_name=employee.department.name if employee.department else None,
            **access,
        )

    @staticmethod
    def to_employee_response(db: Session, employee: Employee) -> EmployeeResponse:
        access = EmployeeService.resolve_employee_access(db, employee)
        data = EmployeeResponse.model_validate(employee)
        return data.model_copy(
            update={
                "department_name": (
                    employee.department.name if employee.department else None
                ),
                **access,
            }
        )

    @staticmethod
    def resolve_user_access(db: Session, user: User) -> dict:
        """Effective role/permissions for login and /auth/me."""
        empty = {
            "role_id": None,
            "role_name": None,
            "department_permissions": {},
            "employee_permissions": {},
            "permissions": {},
            "permissions_overridden": False,
        }
        if user.role == UserRole.ADMIN:
            return empty
        if user.employee_id and user.employee:
            return EmployeeService.resolve_employee_access(db, user.employee)
        extras = dict(user.permissions) if user.permissions else {}
        if user.custom_role_id and user.custom_role:
            department_permissions = dict(user.custom_role.permissions or {})
            extras = EmployeeService._extras_only(extras, department_permissions)
            return {
                "role_id": user.custom_role_id,
                "role_name": user.custom_role.name,
                "department_permissions": department_permissions,
                "employee_permissions": extras,
                "permissions": EmployeeService._merge_permissions(
                    department_permissions, extras
                ),
                "permissions_overridden": bool(extras),
            }
        if extras:
            return {
                **empty,
                "employee_permissions": extras,
                "permissions": extras,
                "permissions_overridden": True,
            }
        return empty

    @staticmethod
    def to_user_response(db: Session, user: User):
        from app.api.v1.schemas.user_schema import UserResponse

        access = EmployeeService.resolve_user_access(db, user)
        data = UserResponse.model_validate(user)
        return data.model_copy(update=access)

    @staticmethod
    def get_employee_permissions(
        db: Session, employee_id: int, company_id: int
    ) -> EmployeePermissionsResponse:
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        if not employee.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee has no login account",
            )
        return EmployeeService._permissions_response(db, employee)

    @staticmethod
    def update_employee_permissions(
        db: Session,
        employee_id: int,
        company_id: int,
        data: EmployeePermissionsUpdate,
    ) -> EmployeePermissionsResponse:
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        user = employee.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee has no login account",
            )

        fields_set = data.model_fields_set
        if (
            data.role_id is None
            and "permissions" not in fields_set
            and "employee_permissions" not in fields_set
            and not data.inherit_from_role
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide role_id, employee_permissions, permissions, and/or inherit_from_role",
            )

        if data.role_id is not None:
            role = (
                db.query(Role)
                .filter(Role.id == data.role_id, Role.company_id == company_id)
                .first()
            )
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role not found for this company",
                )
            user.custom_role_id = role.id

        if user.custom_role_id:
            assigned = (
                db.query(Role)
                .filter(Role.id == user.custom_role_id, Role.company_id == company_id)
                .first()
            )
            department_permissions = dict(assigned.permissions or {}) if assigned else {}
        else:
            template_role = EmployeeService._department_role(db, employee)
            department_permissions = dict(template_role.permissions or {}) if template_role else {}

        if data.inherit_from_role:
            user.permissions = None
        elif "employee_permissions" in fields_set and data.employee_permissions is not None:
            incoming = EmployeeService._permissions_to_dict(data.employee_permissions)
            extras = EmployeeService._extras_only(incoming, department_permissions)
            user.permissions = extras or None
        elif "permissions" in fields_set and data.permissions is not None:
            incoming = EmployeeService._permissions_to_dict(data.permissions)
            extras = EmployeeService._extras_only(incoming, department_permissions)
            user.permissions = extras or None
        elif data.role_id is not None and "permissions" not in fields_set and "employee_permissions" not in fields_set:
            user.permissions = None

        db.commit()
        db.refresh(user)
        db.refresh(employee)
        return EmployeeService._permissions_response(db, employee)
    
    @staticmethod
    def get_all_employees(
        db: Session, 
        company_id: int, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Employee]:
        query = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)  # Exclude soft-deleted employees
        )
        
        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_employee(
        db: Session, 
        employee_id: int, 
        company_id: int, 
        employee_data: EmployeeUpdate
    ) -> Employee:
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        update_data = employee_data.model_dump(exclude_unset=True)
        initial_password = update_data.pop("initial_password", None)
        
        # If email is being updated, check uniqueness per company
        if 'email' in update_data:
            new_email = update_data['email']
            existing_email = db.query(Employee).filter(
                Employee.email == new_email,
                Employee.company_id == company_id,
                Employee.id != employee_id,  # Exclude current employee
                Employee.deleted_at.is_(None)  # Exclude soft-deleted employees
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee email already registered in this company"
                )
        
        for field, value in update_data.items():
            setattr(employee, field, value)

        # Password lives on the User login account, not the Employee row
        user = employee.user
        if initial_password:
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee has no login account to update password"
                )
            user.hashed_password = hash_password_for_storage(initial_password)
            user.force_password_change = True
        if user:
            if "email" in update_data:
                user.email = update_data["email"]
            if "first_name" in update_data or "last_name" in update_data:
                user.full_name = f"{employee.first_name} {employee.last_name}"
            if "is_active" in update_data:
                user.is_active = update_data["is_active"]
        
        db.commit()
        db.refresh(employee)
        
        # Sync to vector database after update
        try:
            sync_service = VectorSyncService()
            sync_service.sync_employee(db, employee.id)
        except Exception as e:
            logger.error(f"Failed to sync employee {employee.id} to vector store after update: {str(e)}")
            # Don't fail the main operation if vector sync fails
        
        return employee
    
    @staticmethod
    def delete_employee(db: Session, employee_id: int, company_id: int) -> None:
        """
        Permanently delete an employee and all related records.
        This will delete:
        - Tasks assigned to the employee
        - Associated user account
        - Attendance records (via CASCADE)
        - Leave requests (via CASCADE)
        - Leave balances (via CASCADE)
        - Vector store entries
        """
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        try:
            # Delete tasks assigned to this employee
            tasks_deleted = db.query(Task).filter(
                Task.assigned_to_employee_id == employee_id,
                Task.company_id == company_id
            ).delete(synchronize_session=False)
            
            # Delete employee attachments (files and records)
            attachments = db.query(EmployeeAttachment).filter(
                EmployeeAttachment.employee_id == employee_id,
                EmployeeAttachment.company_id == company_id
            ).all()
            for attachment in attachments:
                delete_file(attachment.file_path)
            attachments_deleted = db.query(EmployeeAttachment).filter(
                EmployeeAttachment.employee_id == employee_id,
                EmployeeAttachment.company_id == company_id
            ).delete(synchronize_session=False)
            
            # Delete associated user account if it exists
            if employee.user:
                user_id = employee.user.id
                db.delete(employee.user)
            
            # Delete vector store entries for this employee
            try:
                sync_service = VectorSyncService()
                sync_service.delete_content(db, company_id, "employee", employee_id)
            except Exception as e:
                logger.error(f"Failed to delete vector store entries for employee {employee_id}: {str(e)}")
                # Continue with employee deletion even if vector sync fails
            
            # Permanently delete the employee record
            # This will cascade delete:
            # - Attendance records (ondelete="CASCADE")
            # - LeaveRequest records (ondelete="CASCADE")
            # - LeaveBalance records (ondelete="CASCADE")
            db.delete(employee)
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting employee {employee_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete employee: {str(e)}"
            )
    
    @staticmethod
    def get_employee_by_code(db: Session, employee_code: str, company_id: int) -> Optional[Employee]:
        return db.query(Employee).filter(
            Employee.employee_code == employee_code,
            Employee.company_id == company_id,
            Employee.deleted_at.is_(None)  # Exclude soft-deleted employees
        ).first()
    
    @staticmethod
    def get_employees_for_dropdown(
        db: Session, 
        company_id: int, 
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[Employee]:
        """
        Get active employees for dropdown selection (e.g., task assignment).
        Returns only active, non-deleted employees ordered by name.
        Supports search by name (first_name, last_name) or employee_code.
        Limited to prevent returning huge datasets.
        """
        query = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None)  # Exclude soft-deleted employees
        )
        
        # Apply search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_pattern),
                    Employee.last_name.ilike(search_pattern),
                    Employee.employee_code.ilike(search_pattern)
                )
            )
        
        return query.order_by(Employee.first_name, Employee.last_name).limit(limit).all()
    
    @staticmethod
    def upload_employee_attachment(
        db: Session,
        employee_id: int,
        company_id: int,
        file,
        attachment_type: AttachmentType,
        description: Optional[str] = None
    ) -> EmployeeAttachment:
        """
        Upload an attachment for an employee.
        
        Args:
            db: Database session
            employee_id: Employee ID
            company_id: Company ID
            file: Uploaded file
            attachment_type: Type of attachment
            description: Optional description
            
        Returns:
            Created EmployeeAttachment record
        """
        # Verify employee exists and belongs to company
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        # Check if the actual file is an image
        mime_type = getattr(file, 'content_type', None) or ""
        is_actually_image = mime_type.startswith('image/')
        
        # Determine validation:
        # - PROFILE_PHOTO: images only
        # - All other types: accept both images and documents
        if attachment_type == AttachmentType.PROFILE_PHOTO:
            is_image = True  # Must be image
            allow_both = False
        else:
            # All other attachment types accept both images and documents
            is_image = is_actually_image  # Validate based on actual file type
            allow_both = True  # Allow both types
        
        # Save file (pass allow_both flag for validation)
        file_path, file_name, file_size = save_uploaded_file(
            file=file,
            company_id=company_id,
            employee_id=employee_id,
            attachment_type=attachment_type.value,
            is_image=is_image,
            allow_both=allow_both
        )
        
        # Get MIME type
        mime_type = getattr(file, 'content_type', None) or "application/octet-stream"
        
        # Create attachment record
        attachment = EmployeeAttachment(
            company_id=company_id,
            employee_id=employee_id,
            attachment_type=attachment_type,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            description=description
        )
        
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        return attachment
    
    @staticmethod
    def get_employee_attachments(
        db: Session,
        employee_id: int,
        company_id: int,
        attachment_type: Optional[AttachmentType] = None
    ) -> List[EmployeeAttachment]:
        """
        Get all attachments for an employee.
        
        Args:
            db: Database session
            employee_id: Employee ID
            company_id: Company ID
            attachment_type: Optional filter by attachment type
            
        Returns:
            List of EmployeeAttachment records
        """
        # Verify employee exists and belongs to company
        EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        query = db.query(EmployeeAttachment).filter(
            EmployeeAttachment.employee_id == employee_id,
            EmployeeAttachment.company_id == company_id
        )
        
        if attachment_type:
            query = query.filter(EmployeeAttachment.attachment_type == attachment_type)
        
        return query.order_by(EmployeeAttachment.created_at.desc()).all()
    
    @staticmethod
    def get_employee_attachment_by_id(
        db: Session,
        attachment_id: int,
        employee_id: int,
        company_id: int
    ) -> EmployeeAttachment:
        """
        Get a specific attachment by ID.
        
        Args:
            db: Database session
            attachment_id: Attachment ID
            employee_id: Employee ID
            company_id: Company ID
            
        Returns:
            EmployeeAttachment record
            
        Raises:
            HTTPException: If attachment not found
        """
        # Verify employee exists and belongs to company
        EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        attachment = db.query(EmployeeAttachment).filter(
            EmployeeAttachment.id == attachment_id,
            EmployeeAttachment.employee_id == employee_id,
            EmployeeAttachment.company_id == company_id
        ).first()
        
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found"
            )
        
        return attachment
    
    @staticmethod
    def delete_employee_attachment(
        db: Session,
        attachment_id: int,
        employee_id: int,
        company_id: int
    ) -> None:
        """
        Delete an employee attachment.
        
        Args:
            db: Database session
            attachment_id: Attachment ID
            employee_id: Employee ID
            company_id: Company ID
        """
        attachment = EmployeeService.get_employee_attachment_by_id(
            db, attachment_id, employee_id, company_id
        )
        
        try:
            # Delete physical file
            delete_file(attachment.file_path)
            
            # Delete database record
            db.delete(attachment)
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete attachment: {str(e)}"
            )

