from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.lead_model import Lead, ProjectStatus
from app.api.v1.schemas.lead_schema import LeadCreate, LeadUpdate


class LeadService:

    @staticmethod
    def create_lead(db: Session, company_id: int, data: LeadCreate) -> Lead:
        lead = Lead(company_id=company_id, **data.model_dump())
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def get_lead(db: Session, company_id: int, lead_id: int) -> Lead:
        lead = db.query(Lead).filter(
            Lead.id == lead_id,
            Lead.company_id == company_id,
            Lead.deleted_at.is_(None),
        ).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return lead

    @staticmethod
    def list_leads(
        db: Session,
        company_id: int,
        search: Optional[str] = None,
        project_status: Optional[ProjectStatus] = None,
    ) -> List[Lead]:
        query = db.query(Lead).filter(
            Lead.company_id == company_id,
            Lead.deleted_at.is_(None),
        )
        if project_status is not None:
            query = query.filter(Lead.project_status == project_status)
        if search:
            query = query.filter(
                Lead.name.ilike(f"%{search}%")
                | Lead.email.ilike(f"%{search}%")
                | Lead.mobile_number.ilike(f"%{search}%")
                | Lead.project_name.ilike(f"%{search}%")
            )
        return query.order_by(Lead.created_at.desc()).all()

    @staticmethod
    def update_lead(db: Session, company_id: int, lead_id: int, data: LeadUpdate) -> Lead:
        lead = LeadService.get_lead(db, company_id, lead_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(lead, field, value)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def delete_lead(db: Session, company_id: int, lead_id: int) -> None:
        lead = LeadService.get_lead(db, company_id, lead_id)
        lead.deleted_at = datetime.utcnow()
        db.commit()
