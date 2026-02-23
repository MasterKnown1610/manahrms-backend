"""
Event Models for HRMS Calendar Events
Supports company events, holidays, training sessions, announcements, etc.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class EventType(str, enum.Enum):
    """Event type enumeration"""
    COMPANY_EVENT = "COMPANY_EVENT"
    HOLIDAY = "HOLIDAY"
    TRAINING = "TRAINING"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    CUSTOM = "CUSTOM"


class EventVisibility(str, enum.Enum):
    """Event visibility enumeration"""
    ALL = "ALL"  # Visible to all company users
    DEPARTMENT = "DEPARTMENT"  # Visible to specific department
    SELECTED_USERS = "SELECTED_USERS"  # Visible to selected users only


class Event(Base):
    """
    Event model for calendar events (company events, holidays, training, etc.).
    Supports multi-tenant architecture with company_id.
    All times stored in UTC, timezone stored separately for display.
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(Enum(EventType), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    is_all_day = Column(Boolean, default=False, nullable=False)
    
    # Time information (stored in UTC)
    start_time_utc = Column(DateTime, nullable=False, index=True)
    end_time_utc = Column(DateTime, nullable=False, index=True)
    original_timezone = Column(String(100), nullable=False)  # IANA timezone format
    
    # Visibility and access control
    visibility = Column(Enum(EventVisibility), nullable=False, default=EventVisibility.ALL)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    # Creator information
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="events")
    department = relationship("Department")
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_events_company_time', 'company_id', 'start_time_utc'),
        Index('idx_events_company_type', 'company_id', 'event_type'),
        Index('idx_events_company_end_time', 'company_id', 'end_time_utc'),
    )
    
    def __repr__(self):
        return f"<Event {self.id} - {self.title} ({self.event_type.value})>"


class EventParticipant(Base):
    """
    Event participants model (for SELECTED_USERS visibility).
    Tracks which users can see specific events.
    """
    __tablename__ = "event_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    company = relationship("Company")
    user = relationship("User")
    
    # Unique constraint: user can only be added once per event
    __table_args__ = (
        Index('idx_event_participants_event_user', 'event_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<EventParticipant {self.user_id} in Event {self.event_id}>"

