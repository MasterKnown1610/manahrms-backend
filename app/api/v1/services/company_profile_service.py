from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.company_profile_model import CompanyProfile, IndustryType
from app.api.v1.schemas.company_profile_schema import CompanyProfileCreate, CompanyProfileUpdate


class CompanyProfileService:

    @staticmethod
    def get_or_create(db: Session, company_id: int) -> CompanyProfile:
        profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
        if not profile:
            profile = CompanyProfile(company_id=company_id, industry_type=IndustryType.GENERIC)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, company_id: int, data: CompanyProfileUpdate) -> CompanyProfile:
        profile = CompanyProfileService.get_or_create(db, company_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_industry_type(db: Session, company_id: int) -> IndustryType:
        profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
        return profile.industry_type if profile else IndustryType.GENERIC

    @staticmethod
    def is_module_enabled(db: Session, company_id: int, module_key: str) -> bool:
        profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
        if not profile or not profile.enabled_modules:
            return True  # default open — let subscription handle gating
        return bool(profile.enabled_modules.get(module_key, False))
