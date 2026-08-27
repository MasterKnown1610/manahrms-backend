"""
Lead Models — prospective customers and their requirements.
"""
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, Enum, Numeric

from app.db.base import Base


class ProjectStatus(str, enum.Enum):
    NEW = "new"
    QUOTED = "quoted"
    NEGOTIATING = "negotiating"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOST = "lost"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_lead_company", "company_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(254), nullable=True)
    mobile_number = Column(String(20), nullable=True)
    requirement_description = Column(Text, nullable=True)
    project_name = Column(String(200), nullable=True)
    project_description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    quoted_amount = Column(Numeric(14, 2), nullable=True)
    confirmed_amount = Column(Numeric(14, 2), nullable=True)
    project_status = Column(
        Enum(ProjectStatus, values_callable=lambda obj: [e.value for e in obj], name="projectstatus"),
        nullable=False,
        default=ProjectStatus.NEW,
    )
    source = Column(String(50), nullable=False, default="manual")
    exotel_call_sid = Column(String(100), nullable=True, index=True)
    call_recording_url = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
