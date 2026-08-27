from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.role_schema import RoleCreate, RoleUpdate, RoleResponse
from app.api.v1.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    search: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return RoleService.list_roles(db, current_user.company_id, search, department_id)


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return RoleService.create_role(db, current_user.company_id, data)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return RoleService.get_role(db, current_user.company_id, role_id)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return RoleService.update_role(db, current_user.company_id, role_id, data)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: int,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    RoleService.delete_role(db, current_user.company_id, role_id)
