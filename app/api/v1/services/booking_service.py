from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.booking_model import Booking, BookingResource, BookingStatus
from app.api.v1.schemas.booking_schema import (
    BookingCreate, BookingUpdate, BookingResourceCreate, BookingResourceUpdate
)


class BookingService:

    # ── Resources ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_resource(db: Session, company_id: int, data: BookingResourceCreate) -> BookingResource:
        resource = BookingResource(company_id=company_id, **data.model_dump())
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    @staticmethod
    def list_resources(db: Session, company_id: int) -> List[BookingResource]:
        return db.query(BookingResource).filter(
            BookingResource.company_id == company_id,
            BookingResource.is_active == True,
        ).order_by(BookingResource.name).all()

    @staticmethod
    def update_resource(db: Session, company_id: int, resource_id: int, data: BookingResourceUpdate) -> BookingResource:
        resource = db.query(BookingResource).filter(
            BookingResource.id == resource_id,
            BookingResource.company_id == company_id,
        ).first()
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(resource, field, value)
        db.commit()
        db.refresh(resource)
        return resource

    # ── Bookings ───────────────────────────────────────────────────────────────

    @staticmethod
    def create_booking(db: Session, company_id: int, user_id: int, data: BookingCreate) -> Booking:
        if data.end_datetime <= data.start_datetime:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_datetime must be after start_datetime")

        if data.resource_id:
            conflict = db.query(Booking).filter(
                Booking.company_id == company_id,
                Booking.resource_id == data.resource_id,
                Booking.status.notin_([BookingStatus.CANCELLED]),
                Booking.start_datetime < data.end_datetime,
                Booking.end_datetime > data.start_datetime,
            ).first()
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Resource is already booked from {conflict.start_datetime} to {conflict.end_datetime}"
                )

        booking = Booking(
            company_id=company_id,
            booked_by_user_id=user_id,
            **data.model_dump(),
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def get_booking(db: Session, company_id: int, booking_id: int) -> Booking:
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.company_id == company_id,
        ).first()
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        return booking

    @staticmethod
    def list_bookings(
        db: Session, company_id: int,
        status_filter: Optional[BookingStatus] = None,
        resource_id: Optional[int] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Booking]:
        query = db.query(Booking).filter(Booking.company_id == company_id)
        if status_filter:
            query = query.filter(Booking.status == status_filter)
        if resource_id:
            query = query.filter(Booking.resource_id == resource_id)
        if from_dt:
            query = query.filter(Booking.start_datetime >= from_dt)
        if to_dt:
            query = query.filter(Booking.end_datetime <= to_dt)
        return query.order_by(Booking.start_datetime).all()

    @staticmethod
    def update_booking(db: Session, company_id: int, booking_id: int, data: BookingUpdate) -> Booking:
        booking = BookingService.get_booking(db, company_id, booking_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(booking, field, value)
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def cancel_booking(db: Session, company_id: int, booking_id: int, reason: Optional[str] = None) -> Booking:
        booking = BookingService.get_booking(db, company_id, booking_id)
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_reason = reason
        db.commit()
        db.refresh(booking)
        return booking
