"""
Pydantic schemas for Meeting and Calendar APIs
"""
from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.api.v1.models.meeting_model import (
    MeetingPlatform,
    ParticipantRole,
    ParticipantStatus
)


# Request Schemas
class MeetingCreate(BaseModel):
    """Schema for creating a meeting"""
    title: str = Field(..., min_length=1, max_length=255, description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    meeting_link: str = Field(..., min_length=1, max_length=500, description="Meeting URL/link")
    meeting_platform: MeetingPlatform = Field(..., description="Meeting platform")
    start_time: datetime = Field(..., description="Start time in local timezone")
    end_time: datetime = Field(..., description="End time in local timezone")
    timezone: str = Field(..., description="IANA timezone (e.g., Asia/Kolkata)")
    participants: List[int] = Field(default_factory=list, description="List of user IDs to invite")
    
    @validator('timezone')
    def validate_timezone(cls, v):
        from app.api.v1.utils.timezone_utils import validate_timezone
        if not validate_timezone(v):
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone.")
        return v
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("End time must be after start time")
        return v
    
    @validator('meeting_link')
    def validate_meeting_link(cls, v):
        # Basic URL validation
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Meeting link must be a valid URL starting with http:// or https://")
        return v


class MeetingUpdate(BaseModel):
    """Schema for updating a meeting"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    meeting_link: Optional[str] = Field(None, min_length=1, max_length=500)
    meeting_platform: Optional[MeetingPlatform] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    participants: Optional[List[int]] = None
    
    @validator('timezone')
    def validate_timezone(cls, v):
        if v is not None:
            from app.api.v1.utils.timezone_utils import validate_timezone
            if not validate_timezone(v):
                raise ValueError(f"Invalid timezone: {v}")
        return v
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        if v is not None and 'start_time' in values and values['start_time'] is not None:
            if v <= values['start_time']:
                raise ValueError("End time must be after start time")
        return v


class ParticipantUpdate(BaseModel):
    """Schema for updating participant status"""
    status: ParticipantStatus = Field(..., description="New participant status")


# Response Schemas
class ParticipantResponse(BaseModel):
    """Schema for meeting participant response"""
    id: int
    user_id: int
    user_name: str
    user_email: str
    role: ParticipantRole
    status: ParticipantStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class MeetingResponse(BaseModel):
    """Schema for meeting response"""
    id: int
    company_id: int
    title: str
    description: Optional[str]
    meeting_link: str
    meeting_platform: MeetingPlatform
    start_time_utc: datetime
    end_time_utc: datetime
    start_time_local: datetime  # Converted to user's timezone
    end_time_local: datetime     # Converted to user's timezone
    timezone: str
    created_by: Optional[int]
    creator_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    participants: List[ParticipantResponse]
    
    class Config:
        from_attributes = True


class MeetingCreateResponse(BaseModel):
    """Schema for meeting creation response"""
    message: str
    meeting_id: int
    meeting: MeetingResponse


class CalendarEventResponse(BaseModel):
    """Schema for calendar event (simplified for calendar view)"""
    meeting_id: int
    title: str
    start_time: str  # Formatted time string
    end_time: str    # Formatted time string
    timezone: str
    meeting_link: str
    meeting_platform: MeetingPlatform
    participants_count: int


class CalendarDayResponse(BaseModel):
    """Schema for calendar day view response"""
    date: str  # ISO date string
    events: List[CalendarEventResponse]


class CalendarMonthResponse(BaseModel):
    """Schema for calendar month view response"""
    year: int
    month: int
    events: List[CalendarDayResponse]


class TimezoneListResponse(BaseModel):
    """Schema for timezone list response"""
    timezones: List[str]
    common_timezones: List[str]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str

