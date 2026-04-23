from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.schemas.company_profile_schema import (
    CompanyProfileCreate, CompanyProfileUpdate, CompanyProfileResponse
)
from app.api.v1.services.company_profile_service import CompanyProfileService

router = APIRouter(prefix="/company-profile", tags=["Company Profile"])


@router.get("", response_model=CompanyProfileResponse)
async def get_company_profile(
    current_user=Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    return CompanyProfileService.get_or_create(db, current_user.company_id)


@router.put("", response_model=CompanyProfileResponse)
async def upsert_company_profile(
    data: CompanyProfileUpdate,
    current_user=Depends(require_admin_role),
    db: Session = Depends(get_database_session),
):
    return CompanyProfileService.update(db, current_user.company_id, data)
