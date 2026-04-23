from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.booking_schema import (
    BookingCreate, BookingUpdate, BookingResponse,
    BookingResourceCreate, BookingResourceUpdate, BookingResourceResponse,
)
from app.api.v1.models.booking_model import BookingStatus
from app.api.v1.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


class CancelRequest(BaseModel):
    reason: Optional[str] = None


# ── Resources ─────────────────────────────────────────────────────────────────

@router.get("/resources", response_model=List[BookingResourceResponse])
async def list_resources(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.list_resources(db, current_user.company_id)


@router.post("/resources", response_model=BookingResourceResponse, status_code=201)
async def create_resource(
    data: BookingResourceCreate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return BookingService.create_resource(db, current_user.company_id, data)


@router.patch("/resources/{resource_id}", response_model=BookingResourceResponse)
async def update_resource(
    resource_id: int,
    data: BookingResourceUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return BookingService.update_resource(db, current_user.company_id, resource_id, data)


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("", response_model=List[BookingResponse])
async def list_bookings(
    status: Optional[BookingStatus] = Query(None),
    resource_id: Optional[int] = Query(None),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.list_bookings(db, current_user.company_id, status, resource_id, from_dt, to_dt)


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    data: BookingCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.create_booking(db, current_user.company_id, current_user.id, data)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.get_booking(db, current_user.company_id, booking_id)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: int,
    data: BookingUpdate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.update_booking(db, current_user.company_id, booking_id, data)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    data: CancelRequest,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BookingService.cancel_booking(db, current_user.company_id, booking_id, data.reason)
