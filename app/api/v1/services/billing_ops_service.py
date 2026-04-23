from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.billing_ops_model import Invoice, InvoiceItem, InvoiceStatus
from app.api.v1.schemas.billing_ops_schema import InvoiceCreate, InvoiceUpdate


def _generate_invoice_number(db: Session, company_id: int) -> str:
    count = db.query(Invoice).filter(Invoice.company_id == company_id).count()
    today = datetime.utcnow()
    return f"INV-{today.year}{today.month:02d}-{count + 1:04d}"


class BillingOpsService:

    @staticmethod
    def create_invoice(db: Session, company_id: int, user_id: int, data: InvoiceCreate) -> Invoice:
        invoice_number = _generate_invoice_number(db, company_id)

        subtotal = Decimal("0")
        item_records = []
        for item_data in data.items:
            total = item_data.total_price if item_data.total_price is not None else item_data.quantity * item_data.unit_price
            subtotal += total
            item_records.append(InvoiceItem(
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=total,
            ))

        tax_pct = data.tax_percent or Decimal("0")
        tax_amount = (subtotal * tax_pct / Decimal("100")).quantize(Decimal("0.01"))
        discount = data.discount_amount or Decimal("0")
        total_amount = subtotal + tax_amount - discount

        invoice = Invoice(
            company_id=company_id,
            invoice_number=invoice_number,
            client_id=data.client_id,
            title=data.title,
            issue_date=data.issue_date,
            due_date=data.due_date,
            subtotal=subtotal,
            tax_percent=tax_pct,
            tax_amount=tax_amount,
            discount_amount=discount,
            total_amount=total_amount,
            notes=data.notes,
            created_by_user_id=user_id,
        )
        db.add(invoice)
        db.flush()
        for ir in item_records:
            ir.invoice_id = invoice.id
            db.add(ir)
        db.commit()
        db.refresh(invoice)
        return invoice

    @staticmethod
    def get_invoice(db: Session, company_id: int, invoice_id: int) -> Invoice:
        invoice = db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
        ).first()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return invoice

    @staticmethod
    def list_invoices(
        db: Session, company_id: int,
        status_filter: Optional[InvoiceStatus] = None,
        client_id: Optional[int] = None,
    ) -> List[Invoice]:
        query = db.query(Invoice).filter(Invoice.company_id == company_id)
        if status_filter:
            query = query.filter(Invoice.status == status_filter)
        if client_id:
            query = query.filter(Invoice.client_id == client_id)
        return query.order_by(Invoice.created_at.desc()).all()

    @staticmethod
    def update_invoice(db: Session, company_id: int, invoice_id: int, data: InvoiceUpdate) -> Invoice:
        invoice = BillingOpsService.get_invoice(db, company_id, invoice_id)
        if invoice.status == InvoiceStatus.PAID:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a paid invoice")
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] == InvoiceStatus.PAID:
            invoice.paid_at = datetime.utcnow()
        for field, value in update_data.items():
            setattr(invoice, field, value)
        db.commit()
        db.refresh(invoice)
        return invoice

    @staticmethod
    def mark_paid(
        db: Session, company_id: int, invoice_id: int,
        payment_method: Optional[str] = None,
        razorpay_payment_id: Optional[str] = None,
    ) -> Invoice:
        invoice = BillingOpsService.get_invoice(db, company_id, invoice_id)
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        if payment_method:
            invoice.payment_method = payment_method
        if razorpay_payment_id:
            invoice.razorpay_payment_id = razorpay_payment_id
        db.commit()
        db.refresh(invoice)
        return invoice
