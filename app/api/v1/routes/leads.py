from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.lead_schema import LeadCreate, LeadUpdate, LeadResponse
from app.api.v1.models.lead_model import ProjectStatus
from app.api.v1.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    search: Optional[str] = Query(None),
    project_status: Optional[ProjectStatus] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return LeadService.list_leads(db, current_user.company_id, search, project_status)


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    data: LeadCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return LeadService.create_lead(db, current_user.company_id, data)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return LeadService.get_lead(db, current_user.company_id, lead_id)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return LeadService.update_lead(db, current_user.company_id, lead_id, data)


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: int,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    LeadService.delete_lead(db, current_user.company_id, lead_id)
