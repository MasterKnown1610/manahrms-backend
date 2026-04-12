import logging
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.models.task_permission_model import TaskPermission
from app.api.v1.models.user_model import User
from app.api.v1.schemas.task_schema import (
    TaskPermissionGrant,
    MyTaskPermissionItem,
    TaskModulePermissionCode,
)

logger = logging.getLogger(__name__)


class TaskPermissionService:

    @staticmethod
    def has_task_manager_access(db: Session, user: User) -> bool:
        """Return True if the user is an admin OR has been granted task-manager permission."""
        from app.api.v1.models.user_model import UserRole
        if user.role == UserRole.ADMIN:
            return True
        perm = db.query(TaskPermission).filter(
            TaskPermission.company_id == user.company_id,
            TaskPermission.user_id == user.id,
        ).first()
        return perm is not None

    @staticmethod
    def build_my_task_permissions(db: Session, user: User) -> List[MyTaskPermissionItem]:
        """Task-module permissions for the current user (extensible for future grant types)."""
        from app.api.v1.models.user_model import UserRole

        if user.role == UserRole.ADMIN:
            return [
                MyTaskPermissionItem(
                    code=TaskModulePermissionCode.TASK_MANAGER,
                    granted_at=None,
                )
            ]
        perm = db.query(TaskPermission).filter(
            TaskPermission.company_id == user.company_id,
            TaskPermission.user_id == user.id,
        ).first()
        if not perm:
            return []
        return [
            MyTaskPermissionItem(
                code=TaskModulePermissionCode.TASK_MANAGER,
                granted_at=perm.created_at,
            )
        ]

    @staticmethod
    def grant(db: Session, company_id: int, granter_user_id: int, data: TaskPermissionGrant) -> TaskPermission:
        # Ensure target user exists and belongs to the same company
        target = db.query(User).filter(
            User.id == data.user_id,
            User.company_id == company_id,
            User.is_active == True,
        ).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in company",
            )

        existing = db.query(TaskPermission).filter(
            TaskPermission.company_id == company_id,
            TaskPermission.user_id == data.user_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has task-manager permission",
            )

        perm = TaskPermission(
            company_id=company_id,
            user_id=data.user_id,
            granted_by_user_id=granter_user_id,
        )
        db.add(perm)
        db.commit()
        db.refresh(perm)
        logger.info("Task permission granted to user %s by %s", data.user_id, granter_user_id)
        return db.query(TaskPermission).options(
            joinedload(TaskPermission.user),
            joinedload(TaskPermission.granted_by),
        ).filter(TaskPermission.id == perm.id).first()

    @staticmethod
    def revoke(db: Session, company_id: int, target_user_id: int) -> None:
        perm = db.query(TaskPermission).filter(
            TaskPermission.company_id == company_id,
            TaskPermission.user_id == target_user_id,
        ).first()
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task permission not found for this user",
            )
        db.delete(perm)
        db.commit()
        logger.info("Task permission revoked from user %s", target_user_id)

    @staticmethod
    def list_permissions(db: Session, company_id: int) -> List[TaskPermission]:
        return (
            db.query(TaskPermission)
            .options(joinedload(TaskPermission.user), joinedload(TaskPermission.granted_by))
            .filter(TaskPermission.company_id == company_id)
            .order_by(TaskPermission.created_at.desc())
            .all()
        )
