from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.shift_model import Shift, ShiftAssignment
from app.api.v1.schemas.shift_schema import ShiftCreate, ShiftUpdate, ShiftAssignmentCreate


class ShiftService:

    @staticmethod
    def create_shift(db: Session, company_id: int, data: ShiftCreate) -> Shift:
        existing = db.query(Shift).filter(
            Shift.company_id == company_id,
            Shift.name == data.name,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift name already exists")
        shift = Shift(company_id=company_id, **data.model_dump())
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def list_shifts(db: Session, company_id: int) -> List[Shift]:
        return db.query(Shift).filter(
            Shift.company_id == company_id,
            Shift.is_active == True,
        ).order_by(Shift.name).all()

    @staticmethod
    def update_shift(db: Session, company_id: int, shift_id: int, data: ShiftUpdate) -> Shift:
        shift = db.query(Shift).filter(
            Shift.id == shift_id,
            Shift.company_id == company_id,
        ).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(shift, field, value)
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def assign_employee(db: Session, company_id: int, user_id: int, data: ShiftAssignmentCreate) -> ShiftAssignment:
        shift = db.query(Shift).filter(
            Shift.id == data.shift_id,
            Shift.company_id == company_id,
        ).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

        # End any existing active assignments for this employee
        existing = db.query(ShiftAssignment).filter(
            ShiftAssignment.company_id == company_id,
            ShiftAssignment.employee_id == data.employee_id,
            ShiftAssignment.effective_to.is_(None),
        ).all()
        for ea in existing:
            ea.effective_to = data.effective_from

        assignment = ShiftAssignment(
            company_id=company_id,
            shift_id=data.shift_id,
            employee_id=data.employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            assigned_by_user_id=user_id,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def get_employee_shift(db: Session, company_id: int, employee_id: int) -> Optional[ShiftAssignment]:
        return db.query(ShiftAssignment).filter(
            ShiftAssignment.company_id == company_id,
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.effective_to.is_(None),
        ).first()

    @staticmethod
    def list_assignments(db: Session, company_id: int, shift_id: Optional[int] = None) -> List[ShiftAssignment]:
        query = db.query(ShiftAssignment).filter(
            ShiftAssignment.company_id == company_id,
            ShiftAssignment.effective_to.is_(None),
        )
        if shift_id:
            query = query.filter(ShiftAssignment.shift_id == shift_id)
        return query.all()
