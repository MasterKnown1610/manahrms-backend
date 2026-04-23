from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.asset_model import Asset, AssetAssignment, AssetMaintenanceLog, AssetStatus
from app.api.v1.schemas.asset_schema import (
    AssetCreate, AssetUpdate, AssetAssignmentCreate,
    AssetMaintenanceCreate, AssetReturnRequest
)


def _generate_asset_code(db: Session, company_id: int) -> str:
    count = db.query(Asset).filter(Asset.company_id == company_id).count()
    return f"AST{count + 1:06d}"


class AssetService:

    @staticmethod
    def create(db: Session, company_id: int, data: AssetCreate) -> Asset:
        asset_code = _generate_asset_code(db, company_id)
        asset = Asset(company_id=company_id, asset_code=asset_code, **data.model_dump())
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def get(db: Session, company_id: int, asset_id: int) -> Asset:
        asset = db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.company_id == company_id,
            Asset.deleted_at.is_(None),
        ).first()
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        return asset

    @staticmethod
    def list_assets(
        db: Session, company_id: int,
        status_filter: Optional[AssetStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Asset]:
        query = db.query(Asset).filter(
            Asset.company_id == company_id,
            Asset.deleted_at.is_(None),
        )
        if status_filter:
            query = query.filter(Asset.status == status_filter)
        if category:
            query = query.filter(Asset.category.ilike(f"%{category}%"))
        if search:
            query = query.filter(Asset.name.ilike(f"%{search}%"))
        return query.order_by(Asset.name).all()

    @staticmethod
    def update(db: Session, company_id: int, asset_id: int, data: AssetUpdate) -> Asset:
        asset = AssetService.get(db, company_id, asset_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(asset, field, value)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete(db: Session, company_id: int, asset_id: int) -> None:
        asset = AssetService.get(db, company_id, asset_id)
        asset.deleted_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def assign(db: Session, company_id: int, user_id: int, data: AssetAssignmentCreate) -> AssetAssignment:
        asset = AssetService.get(db, company_id, data.asset_id)
        if asset.status == AssetStatus.ASSIGNED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is already assigned")
        assignment = AssetAssignment(
            company_id=company_id,
            asset_id=data.asset_id,
            employee_id=data.employee_id,
            assigned_date=data.assigned_date,
            notes=data.notes,
            assigned_by_user_id=user_id,
        )
        asset.status = AssetStatus.ASSIGNED
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def return_asset(db: Session, company_id: int, assignment_id: int, data: AssetReturnRequest) -> AssetAssignment:
        assignment = db.query(AssetAssignment).filter(
            AssetAssignment.id == assignment_id,
            AssetAssignment.company_id == company_id,
            AssetAssignment.returned_date.is_(None),
        ).first()
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active assignment not found")
        assignment.returned_date = data.returned_date
        asset = AssetService.get(db, company_id, assignment.asset_id)
        asset.status = AssetStatus.AVAILABLE
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def log_maintenance(db: Session, company_id: int, data: AssetMaintenanceCreate) -> AssetMaintenanceLog:
        asset = AssetService.get(db, company_id, data.asset_id)
        log = AssetMaintenanceLog(company_id=company_id, **data.model_dump())
        asset.status = AssetStatus.UNDER_MAINTENANCE
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_assignments(db: Session, company_id: int, asset_id: Optional[int] = None) -> List[AssetAssignment]:
        query = db.query(AssetAssignment).filter(AssetAssignment.company_id == company_id)
        if asset_id:
            query = query.filter(AssetAssignment.asset_id == asset_id)
        return query.order_by(AssetAssignment.assigned_date.desc()).all()
