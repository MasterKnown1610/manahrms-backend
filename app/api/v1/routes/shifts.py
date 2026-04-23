from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.shift_schema import (
    ShiftCreate, ShiftUpdate, ShiftResponse,
    ShiftAssignmentCreate, ShiftAssignmentResponse,
)
from app.api.v1.services.shift_service import ShiftService

router = APIRouter(prefix="/shifts", tags=["Shift Scheduling"])


@router.get("", response_model=List[ShiftResponse])
async def list_shifts(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return ShiftService.list_shifts(db, current_user.company_id)


@router.post("", response_model=ShiftResponse, status_code=201)
async def create_shift(
    data: ShiftCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return ShiftService.create_shift(db, current_user.company_id, data)


@router.patch("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: int,
    data: ShiftUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return ShiftService.update_shift(db, current_user.company_id, shift_id, data)


# ── Assignments ───────────────────────────────────────────────────────────────

@router.get("/assignments", response_model=List[ShiftAssignmentResponse])
async def list_assignments(
    shift_id: Optional[int] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return ShiftService.list_assignments(db, current_user.company_id, shift_id)


@router.post("/assignments", response_model=ShiftAssignmentResponse, status_code=201)
async def assign_employee(
    data: ShiftAssignmentCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return ShiftService.assign_employee(db, current_user.company_id, current_user.id, data)


@router.get("/assignments/my-shift", response_model=Optional[ShiftAssignmentResponse])
async def get_my_shift(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    if not current_user.employee_id:
        return None
    return ShiftService.get_employee_shift(db, current_user.company_id, current_user.employee_id)
