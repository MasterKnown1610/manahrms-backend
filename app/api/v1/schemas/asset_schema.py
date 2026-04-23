from typing import Optional, Any, Dict
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field
from app.api.v1.models.asset_model import AssetStatus


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    location: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    warranty_expiry: Optional[date] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    current_value: Optional[Decimal] = None
    status: Optional[AssetStatus] = None
    location: Optional[str] = None
    warranty_expiry: Optional[date] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    id: int
    company_id: int
    name: str
    asset_code: str
    description: Optional[str] = None
    category: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    status: AssetStatus
    location: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    warranty_expiry: Optional[date] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetAssignmentCreate(BaseModel):
    asset_id: int
    employee_id: int
    assigned_date: date
    notes: Optional[str] = None


class AssetAssignmentResponse(BaseModel):
    id: int
    company_id: int
    asset_id: int
    employee_id: Optional[int] = None
    assigned_date: date
    returned_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetReturnRequest(BaseModel):
    returned_date: date


class AssetMaintenanceCreate(BaseModel):
    asset_id: int
    maintenance_type: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[Decimal] = None
    performed_by: Optional[str] = None
    maintenance_date: date
    next_maintenance_date: Optional[date] = None


class AssetMaintenanceResponse(BaseModel):
    id: int
    company_id: int
    asset_id: int
    maintenance_type: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[Decimal] = None
    performed_by: Optional[str] = None
    maintenance_date: date
    next_maintenance_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
