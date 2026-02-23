"""
Event API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.session import get_database_session
from app.api.v1.schemas.event_schema import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventCreateResponse
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.services.event_service import EventService, check_event_visibility
from app.api.v1.utils.timezone_utils import utc_to_local
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.models.event_model import Event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: Request,
    event_data: EventCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new event.
    - Only Admin/HR can create COMPANY_EVENT
    - Employees can create CUSTOM events (if allowed by plan)
    """
    logger.info(f"Creating event: {event_data.title} by user {current_user.id}")
    
    try:
        event = EventService.create_event(
            db=db,
            company_id=current_user.company_id,
            creator_user_id=current_user.id,
            creator_role=current_user.role.value,
            data=event_data
        )
        
        # Convert to response format with timezone conversion
        user_timezone = event_data.timezone
        start_local = utc_to_local(event.start_time_utc, user_timezone)
        end_local = utc_to_local(event.end_time_utc, user_timezone)
        
        # Get participants
        from app.api.v1.schemas.event_schema import EventParticipantResponse
        participants_data = []
        for participant in event.participants:
            participants_data.append(
                EventParticipantResponse(
                    id=participant.id,
                    user_id=participant.user_id,
                    user_name=participant.user.full_name if participant.user else "Unknown",
                    user_email=participant.user.email if participant.user else "",
                    created_at=participant.created_at
                )
            )
        
        # Get department name
        department_name = None
        if event.department_id and event.department:
            department_name = event.department.name
        
        event_response = EventResponse(
            id=event.id,
            company_id=event.company_id,
            title=event.title,
            description=event.description,
            event_type=event.event_type,
            location=event.location,
            is_all_day=event.is_all_day,
            start_time_utc=event.start_time_utc,
            end_time_utc=event.end_time_utc,
            start_time_local=start_local,
            end_time_local=end_local,
            original_timezone=event.original_timezone,
            visibility=event.visibility,
            department_id=event.department_id,
            department_name=department_name,
            created_by=event.created_by,
            creator_name=current_user.full_name,
            created_at=event.created_at,
            updated_at=event.updated_at,
            participants=participants_data
        )
        
        # Emit WebSocket event
        try:
            from app.api.v1.services.websocket_service import websocket_service
            from app.api.v1.utils.websocket_helper import emit_websocket_event_async
            
            emit_websocket_event_async(
                websocket_service.emit_event_created(
                    db=db,
                    tenant_id=current_user.company_id,
                    event_id=event.id,
                    event_title=event.title,
                    event_type=event.event_type.value,
                    created_by=current_user.id,
                    created_by_name=current_user.full_name
                )
            )
        except Exception as e:
            logger.error(f"Failed to emit event_created WebSocket event: {e}")
        
        return EventCreateResponse(
            message="Event created successfully",
            event_id=event.id,
            event=event_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    timezone: Optional[str] = Query(None, description="User's timezone for display (e.g., Asia/Kolkata)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get event by ID.
    Times are converted to user's timezone if provided.
    Visibility is checked based on user's access.
    """
    # Get user's department ID for visibility check
    user_department_id = None
    if current_user.employee_id:
        from app.api.v1.models.employee_model import Employee
        employee = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
        if employee:
            user_department_id = employee.department_id
    
    event = EventService.get_event_by_id(
        db=db,
        company_id=current_user.company_id,
        event_id=event_id,
        user_id=current_user.id,
        user_department_id=user_department_id,
        user_timezone=timezone
    )
    
    # Use provided timezone or event's timezone
    display_timezone = timezone or event.original_timezone
    start_local = utc_to_local(event.start_time_utc, display_timezone)
    end_local = utc_to_local(event.end_time_utc, display_timezone)
    
    # Get participants
    from app.api.v1.schemas.event_schema import EventParticipantResponse
    participants_data = []
    for participant in event.participants:
        participants_data.append(
            EventParticipantResponse(
                id=participant.id,
                user_id=participant.user_id,
                user_name=participant.user.full_name if participant.user else "Unknown",
                user_email=participant.user.email if participant.user else "",
                created_at=participant.created_at
            )
        )
    
    # Get creator and department names
    creator_name = None
    if event.created_by:
        creator = db.query(User).filter(User.id == event.created_by).first()
        creator_name = creator.full_name if creator else None
    
    department_name = None
    if event.department_id and event.department:
        department_name = event.department.name
    
    return EventResponse(
        id=event.id,
        company_id=event.company_id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        location=event.location,
        is_all_day=event.is_all_day,
        start_time_utc=event.start_time_utc,
        end_time_utc=event.end_time_utc,
        start_time_local=start_local,
        end_time_local=end_local,
        original_timezone=event.original_timezone,
        visibility=event.visibility,
        department_id=event.department_id,
        department_name=department_name,
        created_by=event.created_by,
        creator_name=creator_name,
        created_at=event.created_at,
        updated_at=event.updated_at,
        participants=participants_data
    )


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update an event.
    Only creator or Admin can update.
    """
    logger.info(f"Updating event {event_id} by user {current_user.id}")
    
    event = EventService.update_event(
        db=db,
        company_id=current_user.company_id,
        event_id=event_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        data=event_data
    )
    
    # Convert to response format
    display_timezone = event_data.timezone or event.original_timezone
    start_local = utc_to_local(event.start_time_utc, display_timezone)
    end_local = utc_to_local(event.end_time_utc, display_timezone)
    
    # Get participants
    db.refresh(event)
    from app.api.v1.schemas.event_schema import EventParticipantResponse
    participants_data = []
    for participant in event.participants:
        participants_data.append(
            EventParticipantResponse(
                id=participant.id,
                user_id=participant.user_id,
                user_name=participant.user.full_name if participant.user else "Unknown",
                user_email=participant.user.email if participant.user else "",
                created_at=participant.created_at
            )
        )
    
    # Get creator and department names
    creator_name = None
    if event.created_by:
        creator = db.query(User).filter(User.id == event.created_by).first()
        creator_name = creator.full_name if creator else None
    
    department_name = None
    if event.department_id and event.department:
        department_name = event.department.name
    
    # Emit WebSocket event
    try:
        from app.api.v1.services.websocket_service import websocket_service
        from app.api.v1.utils.websocket_helper import emit_websocket_event_async
        
        emit_websocket_event_async(
            websocket_service.emit_event_updated(
                db=db,
                tenant_id=current_user.company_id,
                event_id=event.id,
                event_title=event.title,
                event_type=event.event_type.value,
                updated_by=current_user.id,
                updated_by_name=current_user.full_name
            )
        )
    except Exception as e:
        logger.error(f"Failed to emit event_updated WebSocket event: {e}")
    
    return EventResponse(
        id=event.id,
        company_id=event.company_id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        location=event.location,
        is_all_day=event.is_all_day,
        start_time_utc=event.start_time_utc,
        end_time_utc=event.end_time_utc,
        start_time_local=start_local,
        end_time_local=end_local,
        original_timezone=event.original_timezone,
        visibility=event.visibility,
        department_id=event.department_id,
        department_name=department_name,
        created_by=event.created_by,
        creator_name=creator_name,
        created_at=event.created_at,
        updated_at=event.updated_at,
        participants=participants_data
    )


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete an event.
    Only creator or Admin can delete.
    """
    logger.info(f"Deleting event {event_id} by user {current_user.id}")
    
    # Get event title before deletion for WebSocket event
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.company_id == current_user.company_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    event_title = event.title
    event_type = event.event_type.value
    
    EventService.delete_event(
        db=db,
        company_id=current_user.company_id,
        event_id=event_id,
        user_id=current_user.id,
        user_role=current_user.role.value
    )
    
    # Emit WebSocket event
    try:
        from app.api.v1.services.websocket_service import websocket_service
        from app.api.v1.utils.websocket_helper import emit_websocket_event_async
        
        emit_websocket_event_async(
            websocket_service.emit_event_cancelled(
                db=db,
                tenant_id=current_user.company_id,
                event_id=event_id,
                event_title=event_title,
                event_type=event_type,
                cancelled_by=current_user.id,
                cancelled_by_name=current_user.full_name
            )
        )
    except Exception as e:
        logger.error(f"Failed to emit event_cancelled WebSocket event: {e}")
    
    return MessageResponse(message="Event deleted successfully")

