"""
CRM Models — clients/patients/customers and their interaction history.
Hospital: patients | Restaurant: customers | Event: clients | SME: prospects
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Boolean, Text, Date, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClientType(str, enum.Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class InteractionType(str, enum.Enum):
    CALL = "call"
    VISIT = "visit"
    EMAIL = "email"
    NOTE = "note"
    APPOINTMENT = "appointment"


class Client(Base):
    __tablename__ = "crm_clients"
    __table_args__ = (
        Index("idx_crm_client_company", "company_id"),
        Index("idx_crm_client_company_active", "company_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    client_type = Column(Enum(ClientType), nullable=False, default=ClientType.INDIVIDUAL)
    name = Column(String(200), nullable=False)
    email = Column(String(254), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    organization_name = Column(String(200), nullable=True)
    # industry_label: "patient" for hospital, "customer" for restaurant, "devotee" for temple
    industry_label = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    custom_attributes = Column(JSONB, nullable=True)  # blood_group for hospital, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = relationship("ClientInteraction", back_populates="client")


class ClientInteraction(Base):
    __tablename__ = "crm_interactions"
    __table_args__ = (
        Index("idx_crm_interaction_company", "company_id"),
        Index("idx_crm_interaction_client", "client_id"),
        Index("idx_crm_interaction_company_date", "company_id", "interaction_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("crm_clients.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(Enum(InteractionType), nullable=False, default=InteractionType.NOTE)
    subject = Column(String(300), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    interaction_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="interactions")
    performed_by = relationship("User")
