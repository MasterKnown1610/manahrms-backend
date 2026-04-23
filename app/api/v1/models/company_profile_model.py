"""
Company Profile Model — stores industry type and enabled modules per company.
This is a non-breaking extension; existing companies have no profile until one is created.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class IndustryType(str, enum.Enum):
    HOSPITAL = "hospital"
    RESTAURANT = "restaurant"
    TEMPLE = "temple"
    SCHOOL = "school"
    EVENT = "event"
    SME = "sme"
    GENERIC = "generic"


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_company_profile_company"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    industry_type = Column(Enum(IndustryType), nullable=False, default=IndustryType.GENERIC)
    enabled_modules = Column(JSONB, nullable=True)       # {"inventory": True, "crm": False, ...}
    custom_roles = Column(JSONB, nullable=True)           # ["doctor", "chef", "priest"]
    custom_fields_config = Column(JSONB, nullable=True)  # field definitions per entity
    industry_settings = Column(JSONB, nullable=True)     # misc per-industry config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", backref="profile", uselist=False)
