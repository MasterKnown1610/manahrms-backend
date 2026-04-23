from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.donation_schema import DonationCreate, DonationUpdate, DonationResponse
from app.api.v1.services.donation_service import DonationService

router = APIRouter(prefix="/donations", tags=["Donations"])


@router.get("", response_model=List[DonationResponse])
async def list_donations(
    purpose: Optional[str] = Query(None),
    donor_name: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return DonationService.list_donations(db, current_user.company_id, purpose, donor_name, from_date, to_date)


@router.post("", response_model=DonationResponse, status_code=201)
async def record_donation(
    data: DonationCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return DonationService.record_donation(db, current_user.company_id, current_user.id, data)


@router.get("/summary")
async def get_donation_summary(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return DonationService.get_summary(db, current_user.company_id)


@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return DonationService.get_donation(db, current_user.company_id, donation_id)


@router.patch("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: int,
    data: DonationUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return DonationService.update_donation(db, current_user.company_id, donation_id, data)
