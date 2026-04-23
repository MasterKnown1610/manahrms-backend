from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from app.api.v1.models.booking_model import BookingStatus


class BookingResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    resource_type: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class BookingResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    resource_type: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class BookingResourceResponse(BaseModel):
    id: int
    company_id: int
    name: str
    resource_type: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: bool
    custom_attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    resource_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    notes: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    custom_attributes: Optional[Dict[str, Any]] = None


class BookingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    resource_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    notes: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status: Optional[BookingStatus] = None
    cancelled_reason: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class BookingResponse(BaseModel):
    id: int
    company_id: int
    resource_id: Optional[int] = None
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    title: str
    notes: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    status: BookingStatus
    booked_by_user_id: Optional[int] = None
    cancelled_reason: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
