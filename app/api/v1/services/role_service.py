from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.api.v1.models.role_model import Role
from app.api.v1.models.department_model import Department
from app.api.v1.schemas.role_schema import RoleCreate, RoleUpdate, RoleResponse


class RoleService:

    @staticmethod
    def _permissions_to_dict(permissions) -> Dict[str, Any]:
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
    def _to_response(role: Role) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            company_id=role.company_id,
            name=role.name,
            description=role.description,
            department_id=role.department_id,
            department_name=role.department.name if role.department else None,
            permissions=role.permissions or {},
            created_at=role.created_at,
            updated_at=role.updated_at,
        )

    @staticmethod
    def _get_role_or_404(db: Session, company_id: int, role_id: int) -> Role:
        role = (
            db.query(Role)
            .options(joinedload(Role.department))
            .filter(Role.id == role_id, Role.company_id == company_id)
            .first()
        )
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )
        return role

    @staticmethod
    def _validate_department(db: Session, company_id: int, department_id: Optional[int]) -> None:
        if department_id is None:
            return
        dept = (
            db.query(Department)
            .filter(
                Department.id == department_id,
                Department.company_id == company_id,
                Department.is_active == True,
            )
            .first()
        )
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department not found for this company",
            )

    @staticmethod
    def create_role(db: Session, company_id: int, data: RoleCreate) -> RoleResponse:
        RoleService._validate_department(db, company_id, data.department_id)

        existing = (
            db.query(Role)
            .filter(Role.company_id == company_id, Role.name == data.name)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{data.name}' already exists",
            )

        role = Role(
            company_id=company_id,
            name=data.name,
            description=data.description,
            department_id=data.department_id,
            permissions=RoleService._permissions_to_dict(data.permissions),
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return RoleService._to_response(RoleService._get_role_or_404(db, company_id, role.id))

    @staticmethod
    def get_role(db: Session, company_id: int, role_id: int) -> RoleResponse:
        return RoleService._to_response(RoleService._get_role_or_404(db, company_id, role_id))

    @staticmethod
    def list_roles(
        db: Session,
        company_id: int,
        search: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> List[RoleResponse]:
        query = (
            db.query(Role)
            .options(joinedload(Role.department))
            .filter(Role.company_id == company_id)
        )
        if department_id is not None:
            query = query.filter(Role.department_id == department_id)
        if search:
            like = f"%{search}%"
            query = query.filter(
                Role.name.ilike(like) | Role.description.ilike(like)
            )
        roles = query.order_by(Role.name.asc()).all()
        return [RoleService._to_response(r) for r in roles]

    @staticmethod
    def update_role(
        db: Session, company_id: int, role_id: int, data: RoleUpdate
    ) -> RoleResponse:
        role = RoleService._get_role_or_404(db, company_id, role_id)
        updates = data.model_dump(exclude_unset=True)

        if "department_id" in updates:
            RoleService._validate_department(db, company_id, updates["department_id"])

        if "name" in updates and updates["name"] != role.name:
            existing = (
                db.query(Role)
                .filter(
                    Role.company_id == company_id,
                    Role.name == updates["name"],
                    Role.id != role_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Role '{updates['name']}' already exists",
                )

        if "permissions" in updates and updates["permissions"] is not None:
            updates["permissions"] = RoleService._permissions_to_dict(updates["permissions"])

        for field, value in updates.items():
            setattr(role, field, value)

        db.commit()
        db.refresh(role)
        return RoleService._to_response(RoleService._get_role_or_404(db, company_id, role.id))

    @staticmethod
    def delete_role(db: Session, company_id: int, role_id: int) -> None:
        role = RoleService._get_role_or_404(db, company_id, role_id)
        db.delete(role)
        db.commit()
