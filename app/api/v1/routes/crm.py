from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.crm_schema import (
    ClientCreate, ClientUpdate, ClientResponse,
    ClientInteractionCreate, ClientInteractionResponse,
)
from app.api.v1.services.crm_service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM"])


# ── Clients ───────────────────────────────────────────────────────────────────

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    search: Optional[str] = Query(None),
    industry_label: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.list_clients(db, current_user.company_id, search, industry_label, is_active)


@router.post("/clients", response_model=ClientResponse, status_code=201)
async def create_client(
    data: ClientCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.create_client(db, current_user.company_id, data)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.get_client(db, current_user.company_id, client_id)


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.update_client(db, current_user.company_id, client_id, data)


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    CRMService.delete_client(db, current_user.company_id, client_id)


# ── Interactions ──────────────────────────────────────────────────────────────

@router.get("/clients/{client_id}/interactions", response_model=List[ClientInteractionResponse])
async def get_interactions(
    client_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.get_client_interactions(db, current_user.company_id, client_id)


@router.post("/interactions", response_model=ClientInteractionResponse, status_code=201)
async def log_interaction(
    data: ClientInteractionCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CRMService.log_interaction(db, current_user.company_id, current_user.id, data)
