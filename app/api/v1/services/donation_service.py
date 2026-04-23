from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.donation_model import Donation
from app.api.v1.schemas.donation_schema import DonationCreate, DonationUpdate


def _generate_receipt_number(db: Session, company_id: int) -> str:
    count = db.query(Donation).filter(Donation.company_id == company_id).count()
    today = datetime.utcnow()
    return f"RCP-{today.year}{today.month:02d}-{count + 1:05d}"


class DonationService:

    @staticmethod
    def record_donation(db: Session, company_id: int, user_id: int, data: DonationCreate) -> Donation:
        receipt_number = _generate_receipt_number(db, company_id)
        donated_at = data.donated_at or datetime.utcnow()
        donation = Donation(
            company_id=company_id,
            receipt_number=receipt_number,
            donated_at=donated_at,
            received_by_user_id=user_id,
            **{k: v for k, v in data.model_dump().items() if k != "donated_at"},
        )
        donation.donated_at = donated_at
        db.add(donation)
        db.commit()
        db.refresh(donation)
        return donation

    @staticmethod
    def get_donation(db: Session, company_id: int, donation_id: int) -> Donation:
        donation = db.query(Donation).filter(
            Donation.id == donation_id,
            Donation.company_id == company_id,
        ).first()
        if not donation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
        return donation

    @staticmethod
    def list_donations(
        db: Session, company_id: int,
        purpose: Optional[str] = None,
        donor_name: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Donation]:
        query = db.query(Donation).filter(Donation.company_id == company_id)
        if purpose:
            query = query.filter(Donation.purpose.ilike(f"%{purpose}%"))
        if donor_name:
            query = query.filter(Donation.donor_name.ilike(f"%{donor_name}%"))
        if from_date:
            query = query.filter(Donation.donated_at >= from_date)
        if to_date:
            query = query.filter(Donation.donated_at <= to_date)
        return query.order_by(Donation.donated_at.desc()).all()

    @staticmethod
    def update_donation(db: Session, company_id: int, donation_id: int, data: DonationUpdate) -> Donation:
        donation = DonationService.get_donation(db, company_id, donation_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(donation, field, value)
        db.commit()
        db.refresh(donation)
        return donation

    @staticmethod
    def get_summary(db: Session, company_id: int) -> dict:
        from sqlalchemy import func
        total = db.query(func.sum(Donation.amount)).filter(Donation.company_id == company_id).scalar() or 0
        count = db.query(func.count(Donation.id)).filter(Donation.company_id == company_id).scalar() or 0
        return {"total_donations": count, "total_amount": float(total)}
