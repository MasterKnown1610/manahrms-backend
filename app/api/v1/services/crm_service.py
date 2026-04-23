from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.crm_model import Client, ClientInteraction
from app.api.v1.schemas.crm_schema import ClientCreate, ClientUpdate, ClientInteractionCreate


class CRMService:

    @staticmethod
    def create_client(db: Session, company_id: int, data: ClientCreate) -> Client:
        client = Client(company_id=company_id, **data.model_dump())
        db.add(client)
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def get_client(db: Session, company_id: int, client_id: int) -> Client:
        client = db.query(Client).filter(
            Client.id == client_id,
            Client.company_id == company_id,
            Client.deleted_at.is_(None),
        ).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    @staticmethod
    def list_clients(
        db: Session, company_id: int,
        search: Optional[str] = None,
        industry_label: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> List[Client]:
        query = db.query(Client).filter(
            Client.company_id == company_id,
            Client.deleted_at.is_(None),
        )
        if is_active is not None:
            query = query.filter(Client.is_active == is_active)
        if industry_label:
            query = query.filter(Client.industry_label == industry_label)
        if search:
            query = query.filter(Client.name.ilike(f"%{search}%"))
        return query.order_by(Client.name).all()

    @staticmethod
    def update_client(db: Session, company_id: int, client_id: int, data: ClientUpdate) -> Client:
        client = CRMService.get_client(db, company_id, client_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(client, field, value)
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def delete_client(db: Session, company_id: int, client_id: int) -> None:
        client = CRMService.get_client(db, company_id, client_id)
        client.deleted_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def log_interaction(
        db: Session, company_id: int, user_id: int, data: ClientInteractionCreate
    ) -> ClientInteraction:
        CRMService.get_client(db, company_id, data.client_id)
        interaction = ClientInteraction(
            company_id=company_id,
            performed_by_user_id=user_id,
            interaction_date=data.interaction_date or datetime.utcnow(),
            **{k: v for k, v in data.model_dump().items() if k != "interaction_date"},
        )
        if data.interaction_date:
            interaction.interaction_date = data.interaction_date
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction

    @staticmethod
    def get_client_interactions(db: Session, company_id: int, client_id: int) -> List[ClientInteraction]:
        CRMService.get_client(db, company_id, client_id)
        return db.query(ClientInteraction).filter(
            ClientInteraction.company_id == company_id,
            ClientInteraction.client_id == client_id,
        ).order_by(ClientInteraction.interaction_date.desc()).all()
