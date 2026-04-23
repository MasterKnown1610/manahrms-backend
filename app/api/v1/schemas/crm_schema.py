from typing import Optional, Any, Dict, List
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr
from app.api.v1.models.crm_model import ClientType, InteractionType


class ClientCreate(BaseModel):
    client_type: ClientType = ClientType.INDIVIDUAL
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    organization_name: Optional[str] = None
    industry_label: Optional[str] = None  # "patient", "customer", "devotee"
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class ClientUpdate(BaseModel):
    client_type: Optional[ClientType] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    organization_name: Optional[str] = None
    industry_label: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ClientResponse(BaseModel):
    id: int
    company_id: int
    client_type: ClientType
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    organization_name: Optional[str] = None
    industry_label: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientInteractionCreate(BaseModel):
    client_id: int
    interaction_type: InteractionType = InteractionType.NOTE
    subject: Optional[str] = None
    notes: Optional[str] = None
    interaction_date: Optional[datetime] = None


class ClientInteractionResponse(BaseModel):
    id: int
    company_id: int
    client_id: int
    interaction_type: InteractionType
    subject: Optional[str] = None
    notes: Optional[str] = None
    performed_by_user_id: Optional[int] = None
    interaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
