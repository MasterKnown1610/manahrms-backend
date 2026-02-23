"""
Event Service for Calendar Events Management
Handles CRUD operations, visibility control, and timezone conversions
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime
import logging

from app.api.v1.models.event_model import Event, EventParticipant, EventType, EventVisibility
from app.api.v1.models.user_model import User
from app.api.v1.models.department_model import Department
from app.api.v1.schemas.event_schema import EventCreate, EventUpdate
from app.api.v1.utils.timezone_utils import local_to_utc, validate_timezone
from app.api.v1.utils.error_handler import raise_http_exception
from app.api.v1.schemas.websocket_schema import SubscriptionPlan


logger = logging.getLogger(__name__)


def get_subscription_plan(db: Session, company_id: int) -> SubscriptionPlan:
    """
    Get subscription plan for a company.
    TODO: Implement actual subscription plan lookup from database
    """
    return SubscriptionPlan.PRO


def check_event_feature_access(db: Session, company_id: int, event_type: EventType, action: str = "create") -> None:
    """
    Check if company's subscription plan allows event features.
    
    Args:
        db: Database session
        company_id: Company ID
        event_type: Type of event being created
        action: Action being performed
    
    Raises:
        HTTPException if feature is not available
    """
    plan = get_subscription_plan(db, company_id)
    
    # Free Trial: Limited events (max 10 per month)
    if plan == SubscriptionPlan.BASIC:
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        event_count = db.query(Event).filter(
            and_(
                Event.company_id == company_id,
                Event.created_at >= start_of_month
            )
        ).count()
        
        if event_count >= 10:
            raise_http_exception(
                message="Event limit reached. Upgrade to Basic plan for unlimited events.",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="EVENT_LIMIT_EXCEEDED"
            )
    
    # Department visibility requires Pro plan
    # This will be checked in the create/update methods
    
    logger.debug(f"Event feature access granted for company {company_id}, plan: {plan.value}")


def check_event_visibility(
    db: Session,
    event: Event,
    user_id: int,
    user_department_id: Optional[int] = None
) -> bool:
    """
    Check if a user can view an event based on visibility settings.
    
    Args:
        db: Database session
        event: Event object
        user_id: User ID
        user_department_id: User's department ID (optional)
    
    Returns:
        True if user can view, False otherwise
    """
    if event.visibility == EventVisibility.ALL:
        return True
    
    if event.visibility == EventVisibility.DEPARTMENT:
        if event.department_id and user_department_id:
            return event.department_id == user_department_id
        return False
    
    if event.visibility == EventVisibility.SELECTED_USERS:
        participant = db.query(EventParticipant).filter(
            and_(
                EventParticipant.event_id == event.id,
                EventParticipant.user_id == user_id
            )
        ).first()
        return participant is not None
    
    return False


class EventService:
    """Service for event management operations"""
    
    @staticmethod
    def create_event(
        db: Session,
        company_id: int,
        creator_user_id: int,
        creator_role: str,
        data: EventCreate
    ) -> Event:
        """
        Create a new event.
        
        Args:
            db: Database session
            company_id: Company ID
            creator_user_id: User ID creating the event
            creator_role: Creator's role
            data: Event creation data
        
        Returns:
            Created event
        """
        logger.info(f"Creating event: {data.title} for company {company_id}")
        
        # Check subscription feature access
        check_event_feature_access(db, company_id, data.event_type, "create")
        
        # Role-based permission checks
        if data.event_type == EventType.COMPANY_EVENT:
            if creator_role not in ["admin"]:
                raise_http_exception(
                    message="Only Admin/HR can create company events",
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code="INSUFFICIENT_PERMISSIONS"
                )
        
        # Department visibility requires Pro plan
        if data.visibility == EventVisibility.DEPARTMENT:
            plan = get_subscription_plan(db, company_id)
            if plan not in [SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE]:
                raise_http_exception(
                    message="Department-based visibility requires Pro plan or higher",
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code="SUBSCRIPTION_REQUIRED"
                )
            
            # Validate department belongs to company
            department = db.query(Department).filter(
                and_(
                    Department.id == data.department_id,
                    Department.company_id == company_id
                )
            ).first()
            
            if not department:
                raise_http_exception(
                    message="Department not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="DEPARTMENT_NOT_FOUND"
                )
        
        # Validate timezone
        if not validate_timezone(data.timezone):
            raise_http_exception(
                message=f"Invalid timezone: {data.timezone}",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_TIMEZONE"
            )
        
        # Convert local times to UTC
        start_time_utc = local_to_utc(data.start_time, data.timezone)
        end_time_utc = local_to_utc(data.end_time, data.timezone)
        
        # Validate selected users if visibility is SELECTED_USERS
        if data.visibility == EventVisibility.SELECTED_USERS and data.selected_user_ids:
            users = db.query(User).filter(
                and_(
                    User.id.in_(data.selected_user_ids),
                    User.company_id == company_id,
                    User.is_active == True
                )
            ).all()
            
            if len(users) != len(data.selected_user_ids):
                raise_http_exception(
                    message="Some selected users not found or belong to different company",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_USERS"
                )
        
        # Create event
        event = Event(
            company_id=company_id,
            title=data.title,
            description=data.description,
            event_type=data.event_type,
            location=data.location,
            is_all_day=data.is_all_day,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            original_timezone=data.timezone,
            visibility=data.visibility,
            department_id=data.department_id if data.visibility == EventVisibility.DEPARTMENT else None,
            created_by=creator_user_id
        )
        db.add(event)
        db.flush()  # Get event ID
        
        # Add participants if visibility is SELECTED_USERS
        if data.visibility == EventVisibility.SELECTED_USERS and data.selected_user_ids:
            for user_id in data.selected_user_ids:
                participant = EventParticipant(
                    event_id=event.id,
                    company_id=company_id,
                    user_id=user_id
                )
                db.add(participant)
        
        db.commit()
        db.refresh(event)
        
        logger.info(f"Event created successfully: {event.id}")
        return event
    
    @staticmethod
    def get_event_by_id(
        db: Session,
        company_id: int,
        event_id: int,
        user_id: int,
        user_department_id: Optional[int] = None,
        user_timezone: Optional[str] = None
    ) -> Event:
        """
        Get event by ID with visibility check.
        
        Args:
            db: Database session
            company_id: Company ID
            event_id: Event ID
            user_id: User ID (for visibility check)
            user_department_id: User's department ID
            user_timezone: User's timezone for display
        
        Returns:
            Event object
        """
        event = db.query(Event).options(
            joinedload(Event.participants).joinedload(EventParticipant.user),
            joinedload(Event.department)
        ).filter(
            and_(
                Event.id == event_id,
                Event.company_id == company_id
            )
        ).first()
        
        if not event:
            raise_http_exception(
                message="Event not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="EVENT_NOT_FOUND"
            )
        
        # Check visibility
        if not check_event_visibility(db, event, user_id, user_department_id):
            raise_http_exception(
                message="You don't have permission to view this event",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="EVENT_ACCESS_DENIED"
            )
        
        return event
    
    @staticmethod
    def update_event(
        db: Session,
        company_id: int,
        event_id: int,
        user_id: int,
        user_role: str,
        data: EventUpdate
    ) -> Event:
        """
        Update an event.
        Only creator or Admin can update.
        
        Args:
            db: Database session
            company_id: Company ID
            event_id: Event ID
            user_id: User ID making the update
            user_role: User role
            data: Update data
        
        Returns:
            Updated event
        """
        event = db.query(Event).filter(
            and_(
                Event.id == event_id,
                Event.company_id == company_id
            )
        ).first()
        
        if not event:
            raise_http_exception(
                message="Event not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="EVENT_NOT_FOUND"
            )
        
        # Check permissions: Creator or Admin only
        is_creator = event.created_by == user_id
        is_admin = user_role == "admin"
        
        if not (is_creator or is_admin):
            raise_http_exception(
                message="Only event creator or admin can update this event",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="INSUFFICIENT_PERMISSIONS"
            )
        
        # Update fields
        if data.title is not None:
            event.title = data.title
        if data.description is not None:
            event.description = data.description
        if data.event_type is not None:
            event.event_type = data.event_type
        if data.location is not None:
            event.location = data.location
        if data.is_all_day is not None:
            event.is_all_day = data.is_all_day
        
        # Update times if provided
        if data.start_time is not None or data.end_time is not None or data.timezone is not None:
            timezone = data.timezone or event.original_timezone
            
            if not validate_timezone(timezone):
                raise_http_exception(
                    message=f"Invalid timezone: {timezone}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_TIMEZONE"
                )
            
            start_time = data.start_time if data.start_time else event.start_time_utc
            end_time = data.end_time if data.end_time else event.end_time_utc
            
            # Convert to UTC
            start_time_utc = local_to_utc(start_time, timezone)
            end_time_utc = local_to_utc(end_time, timezone)
            
            event.start_time_utc = start_time_utc
            event.end_time_utc = end_time_utc
            event.original_timezone = timezone
        
        # Update visibility if provided
        if data.visibility is not None:
            # Department visibility requires Pro plan
            if data.visibility == EventVisibility.DEPARTMENT:
                plan = get_subscription_plan(db, company_id)
                if plan not in [SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE]:
                    raise_http_exception(
                        message="Department-based visibility requires Pro plan or higher",
                        status_code=status.HTTP_403_FORBIDDEN,
                        error_code="SUBSCRIPTION_REQUIRED"
                    )
            
            event.visibility = data.visibility
            
            if data.department_id is not None:
                event.department_id = data.department_id
        
        # Update participants if visibility changed to SELECTED_USERS
        if data.visibility == EventVisibility.SELECTED_USERS and data.selected_user_ids is not None:
            # Remove existing participants
            db.query(EventParticipant).filter(
                EventParticipant.event_id == event_id
            ).delete()
            
            # Add new participants
            for participant_user_id in data.selected_user_ids:
                user = db.query(User).filter(
                    and_(
                        User.id == participant_user_id,
                        User.company_id == company_id,
                        User.is_active == True
                    )
                ).first()
                
                if user:
                    participant = EventParticipant(
                        event_id=event_id,
                        company_id=company_id,
                        user_id=participant_user_id
                    )
                    db.add(participant)
        
        db.commit()
        db.refresh(event)
        
        logger.info(f"Event updated: {event_id}")
        return event
    
    @staticmethod
    def delete_event(
        db: Session,
        company_id: int,
        event_id: int,
        user_id: int,
        user_role: str
    ) -> None:
        """
        Delete an event.
        Only creator or Admin can delete.
        
        Args:
            db: Database session
            company_id: Company ID
            event_id: Event ID
            user_id: User ID making the delete
            user_role: User role
        """
        event = db.query(Event).filter(
            and_(
                Event.id == event_id,
                Event.company_id == company_id
            )
        ).first()
        
        if not event:
            raise_http_exception(
                message="Event not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="EVENT_NOT_FOUND"
            )
        
        # Check permissions: Creator or Admin only
        is_creator = event.created_by == user_id
        is_admin = user_role == "admin"
        
        if not (is_creator or is_admin):
            raise_http_exception(
                message="Only event creator or admin can delete this event",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="INSUFFICIENT_PERMISSIONS"
            )
        
        db.delete(event)
        db.commit()
        
        logger.info(f"Event deleted: {event_id}")

