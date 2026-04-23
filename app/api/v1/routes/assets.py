from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.asset_schema import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetAssignmentCreate, AssetAssignmentResponse,
    AssetReturnRequest,
    AssetMaintenanceCreate, AssetMaintenanceResponse,
)
from app.api.v1.models.asset_model import AssetStatus
from app.api.v1.services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    status: Optional[AssetStatus] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return AssetService.list_assets(db, current_user.company_id, status, category, search)


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    data: AssetCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return AssetService.create(db, current_user.company_id, data)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return AssetService.get(db, current_user.company_id, asset_id)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    data: AssetUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return AssetService.update(db, current_user.company_id, asset_id, data)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: int,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    AssetService.delete(db, current_user.company_id, asset_id)


# ── Assignments ───────────────────────────────────────────────────────────────

@router.get("/assignments/list", response_model=List[AssetAssignmentResponse])
async def list_assignments(
    asset_id: Optional[int] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return AssetService.list_assignments(db, current_user.company_id, asset_id)


@router.post("/assignments", response_model=AssetAssignmentResponse, status_code=201)
async def assign_asset(
    data: AssetAssignmentCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return AssetService.assign(db, current_user.company_id, current_user.id, data)


@router.post("/assignments/{assignment_id}/return", response_model=AssetAssignmentResponse)
async def return_asset(
    assignment_id: int,
    data: AssetReturnRequest,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return AssetService.return_asset(db, current_user.company_id, assignment_id, data)


# ── Maintenance ───────────────────────────────────────────────────────────────

@router.post("/maintenance", response_model=AssetMaintenanceResponse, status_code=201)
async def log_maintenance(
    data: AssetMaintenanceCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return AssetService.log_maintenance(db, current_user.company_id, data)
