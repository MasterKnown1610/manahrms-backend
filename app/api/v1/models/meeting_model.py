"""
Meeting and Calendar Models for Multi-tenant HRMS
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class MeetingPlatform(str, enum.Enum):
    """Meeting platform enumeration"""
    GOOGLE_MEET = "GOOGLE_MEET"
    MS_TEAMS = "MS_TEAMS"
    ZOOM = "ZOOM"
    OTHER = "OTHER"


class ParticipantRole(str, enum.Enum):
    """Meeting participant role"""
    HOST = "HOST"
    PARTICIPANT = "PARTICIPANT"


class ParticipantStatus(str, enum.Enum):
    """Meeting participant status"""
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class Meeting(Base):
    """
    Meeting model for calendar and meeting management.
    Supports multi-tenant architecture with company_id.
    All times stored in UTC, timezone stored separately for display.
    """
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Meeting details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    meeting_link = Column(String(500), nullable=False)
    meeting_platform = Column(Enum(MeetingPlatform), nullable=False, default=MeetingPlatform.OTHER)
    
    # Time information (stored in UTC)
    start_time_utc = Column(DateTime, nullable=False, index=True)
    end_time_utc = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(100), nullable=False)  # IANA timezone format, e.g., "Asia/Kolkata"
    
    # Creator information
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="meetings")
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_meetings_company_time', 'company_id', 'start_time_utc'),
        Index('idx_meetings_company_end_time', 'company_id', 'end_time_utc'),
    )
    
    def __repr__(self):
        return f"<Meeting {self.id} - {self.title} ({self.company_id})>"


class MeetingParticipant(Base):
    """
    Meeting participants model.
    Tracks user participation in meetings with roles and status.
    """
    __tablename__ = "meeting_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Participant details
    role = Column(Enum(ParticipantRole), nullable=False, default=ParticipantRole.PARTICIPANT)
    status = Column(Enum(ParticipantStatus), nullable=False, default=ParticipantStatus.INVITED)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="participants")
    company = relationship("Company")
    user = relationship("User")
    
    # Unique constraint: user can only be added once per meeting
    __table_args__ = (
        Index('idx_participants_meeting_user', 'meeting_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<MeetingParticipant {self.user_id} in Meeting {self.meeting_id} ({self.role})>"

