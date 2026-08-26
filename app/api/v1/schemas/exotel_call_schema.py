from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class ExotelStreamUrlResponse(BaseModel):
    url: str


class ExotelCallCompleteResponse(BaseModel):
    status: str
    lead_id: Optional[int] = None
    call_sid: Optional[str] = None
    message: Optional[str] = None


class ExotelCallSessionResponse(BaseModel):
    call_sid: str
    mobile_number: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    requirement: Optional[str] = None
    recording_url: Optional[str] = None
    lead_created: bool = False
    lead_id: Optional[int] = None
    transcript_excerpt: Optional[str] = None
