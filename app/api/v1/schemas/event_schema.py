"""
Pydantic schemas for Event APIs
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date

from app.api.v1.models.event_model import EventType, EventVisibility


# Request Schemas
class EventCreate(BaseModel):
    """Schema for creating an event"""
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    event_type: EventType = Field(..., description="Type of event")
    location: Optional[str] = Field(None, max_length=255, description="Event location")
    is_all_day: bool = Field(False, description="Whether event is all-day")
    start_time: datetime = Field(..., description="Start time in local timezone")
    end_time: datetime = Field(..., description="End time in local timezone")
    timezone: str = Field(..., description="IANA timezone (e.g., Asia/Kolkata)")
    visibility: EventVisibility = Field(EventVisibility.ALL, description="Event visibility")
    department_id: Optional[int] = Field(None, description="Department ID (required if visibility is DEPARTMENT)")
    selected_user_ids: Optional[List[int]] = Field(None, description="User IDs (required if visibility is SELECTED_USERS)")
    
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
    
    @validator('department_id')
    def validate_department_for_visibility(cls, v, values):
        if 'visibility' in values and values['visibility'] == EventVisibility.DEPARTMENT and not v:
            raise ValueError("department_id is required when visibility is DEPARTMENT")
        return v
    
    @validator('selected_user_ids')
    def validate_users_for_visibility(cls, v, values):
        if 'visibility' in values and values['visibility'] == EventVisibility.SELECTED_USERS:
            if not v or len(v) == 0:
                raise ValueError("selected_user_ids is required when visibility is SELECTED_USERS")
        return v


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    location: Optional[str] = Field(None, max_length=255)
    is_all_day: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    visibility: Optional[EventVisibility] = None
    department_id: Optional[int] = None
    selected_user_ids: Optional[List[int]] = None
    
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


# Response Schemas
class EventParticipantResponse(BaseModel):
    """Schema for event participant response"""
    id: int
    user_id: int
    user_name: str
    user_email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Schema for event response"""
    id: int
    company_id: int
    title: str
    description: Optional[str]
    event_type: EventType
    location: Optional[str]
    is_all_day: bool
    start_time_utc: datetime
    end_time_utc: datetime
    start_time_local: datetime  # Converted to user's timezone
    end_time_local: datetime     # Converted to user's timezone
    original_timezone: str
    visibility: EventVisibility
    department_id: Optional[int]
    department_name: Optional[str]
    created_by: Optional[int]
    creator_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    participants: List[EventParticipantResponse]
    
    class Config:
        from_attributes = True


class EventCreateResponse(BaseModel):
    """Schema for event creation response"""
    message: str
    event_id: int
    event: EventResponse


class CalendarEventItem(BaseModel):
    """Schema for calendar event item (unified for meetings and events)"""
    id: int
    title: str
    start_time: str  # Formatted time string
    end_time: str    # Formatted time string
    start_time_iso: str  # ISO format
    end_time_iso: str    # ISO format
    timezone: str
    type: str  # "MEETING" or event type value
    location: Optional[str] = None
    is_all_day: bool = False
    description: Optional[str] = None


class CalendarDayUnifiedResponse(BaseModel):
    """Schema for unified calendar day response (meetings + events)"""
    date: str  # ISO date string
    timezone: str
    meetings: List[CalendarEventItem]
    events: List[CalendarEventItem]


class CalendarMonthDayResponse(BaseModel):
    """Schema for a single day in calendar month view"""
    date: str  # ISO date string
    meetings: List[CalendarEventItem]
    events: List[CalendarEventItem]


class CalendarMonthUnifiedResponse(BaseModel):
    """Schema for unified calendar month response (meetings + events)"""
    year: int
    month: int
    timezone: str
    days: List[CalendarMonthDayResponse]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str

