from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.billing_ops_schema import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from app.api.v1.models.billing_ops_model import InvoiceStatus
from app.api.v1.services.billing_ops_service import BillingOpsService

router = APIRouter(prefix="/billing", tags=["Billing Operations"])


class MarkPaidRequest(BaseModel):
    payment_method: Optional[str] = None
    razorpay_payment_id: Optional[str] = None


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[InvoiceStatus] = Query(None),
    client_id: Optional[int] = Query(None),
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BillingOpsService.list_invoices(db, current_user.company_id, status, client_id)


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BillingOpsService.create_invoice(db, current_user.company_id, current_user.id, data)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BillingOpsService.get_invoice(db, current_user.company_id, invoice_id)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return BillingOpsService.update_invoice(db, current_user.company_id, invoice_id, data)


@router.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_paid(
    invoice_id: int,
    data: MarkPaidRequest,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return BillingOpsService.mark_paid(
        db, current_user.company_id, invoice_id,
        data.payment_method, data.razorpay_payment_id
    )
