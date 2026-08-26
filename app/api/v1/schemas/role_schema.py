from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ModulePermission(BaseModel):
    view: bool = False
    create: bool = False
    edit: bool = False
    delete: bool = False


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    department_id: Optional[int] = None
    permissions: Dict[str, ModulePermission] = Field(default_factory=dict)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    department_id: Optional[int] = None
    permissions: Optional[Dict[str, ModulePermission]] = None


class RoleResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
