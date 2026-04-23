from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.api.v1.models.company_profile_model import IndustryType


class CompanyProfileCreate(BaseModel):
    industry_type: IndustryType = IndustryType.GENERIC
    enabled_modules: Optional[Dict[str, bool]] = None
    custom_roles: Optional[List[str]] = None
    custom_fields_config: Optional[Dict[str, Any]] = None
    industry_settings: Optional[Dict[str, Any]] = None


class CompanyProfileUpdate(BaseModel):
    industry_type: Optional[IndustryType] = None
    enabled_modules: Optional[Dict[str, bool]] = None
    custom_roles: Optional[List[str]] = None
    custom_fields_config: Optional[Dict[str, Any]] = None
    industry_settings: Optional[Dict[str, Any]] = None


class CompanyProfileResponse(BaseModel):
    id: int
    company_id: int
    industry_type: IndustryType
    enabled_modules: Optional[Dict[str, bool]] = None
    custom_roles: Optional[List[str]] = None
    custom_fields_config: Optional[Dict[str, Any]] = None
    industry_settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
