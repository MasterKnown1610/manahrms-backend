"""
Meeting and Calendar API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
import logging

from app.db.session import get_database_session
from app.api.v1.schemas.meeting_schema import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingCreateResponse,
    CalendarEventResponse,
    CalendarDayResponse,
    CalendarMonthResponse,
    TimezoneListResponse,
    MessageResponse,
    ParticipantUpdate
)
from app.api.v1.services.meeting_service import MeetingService
from app.api.v1.services.calendar_service import CalendarService
from app.api.v1.utils.timezone_utils import (
    get_all_timezones,
    get_common_timezones,
    utc_to_local
)
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.models.meeting_model import Meeting, MeetingParticipant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["Meetings & Calendar"])


@router.get("/timezones", response_model=TimezoneListResponse)
async def get_timezones():
    """
    Get list of all available timezones and common timezones.
    Used for timezone dropdown in frontend.
    """
    return TimezoneListResponse(
        timezones=get_all_timezones(),
        common_timezones=get_common_timezones()
    )


@router.post("", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    request: Request,
    meeting_data: MeetingCreate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new meeting.
    Only users within the same company can be added as participants.
    Creator automatically becomes HOST.
    """
    logger.info(f"Creating meeting: {meeting_data.title} by user {current_user.id}")
    
    try:
        meeting = MeetingService.create_meeting(
            db=db,
            company_id=current_user.company_id,
            creator_user_id=current_user.id,
            data=meeting_data
        )
        
        # Convert to response format with timezone conversion
        user_timezone = meeting_data.timezone  # Use meeting timezone for display
        start_local = utc_to_local(meeting.start_time_utc, user_timezone)
        end_local = utc_to_local(meeting.end_time_utc, user_timezone)
        
        # Get participants - need to create ParticipantResponse objects
        from app.api.v1.schemas.meeting_schema import ParticipantResponse
        participants_data = []
        for participant in meeting.participants:
            participants_data.append(
                ParticipantResponse(
                    id=participant.id,
                    user_id=participant.user_id,
                    user_name=participant.user.full_name if participant.user else "Unknown",
                    user_email=participant.user.email if participant.user else "",
                    role=participant.role,
                    status=participant.status,
                    created_at=participant.created_at
                )
            )
        
        meeting_response = MeetingResponse(
            id=meeting.id,
            company_id=meeting.company_id,
            title=meeting.title,
            description=meeting.description,
            meeting_link=meeting.meeting_link,
            meeting_platform=meeting.meeting_platform,
            start_time_utc=meeting.start_time_utc,
            end_time_utc=meeting.end_time_utc,
            start_time_local=start_local,
            end_time_local=end_local,
            timezone=meeting.timezone,
            created_by=meeting.created_by,
            creator_name=current_user.full_name,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
            participants=participants_data
        )
        
        # Emit WebSocket event
        try:
            from app.api.v1.services.websocket_service import websocket_service
            from app.api.v1.utils.websocket_helper import emit_websocket_event_async
            
            emit_websocket_event_async(
                websocket_service.emit_meeting_created(
                    db=db,
                    tenant_id=current_user.company_id,
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    created_by=current_user.id,
                    created_by_name=current_user.full_name
                )
            )
        except Exception as e:
            logger.error(f"Failed to emit meeting_created WebSocket event: {e}")
        
        return MeetingCreateResponse(
            message="Meeting created successfully",
            meeting_id=meeting.id,
            meeting=meeting_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating meeting: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create meeting: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    timezone: Optional[str] = Query(None, description="User's timezone for display (e.g., Asia/Kolkata)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get meeting by ID.
    Times are converted to user's timezone if provided.
    """
    meeting = MeetingService.get_meeting_by_id(
        db=db,
        company_id=current_user.company_id,
        meeting_id=meeting_id,
        user_timezone=timezone
    )
    
    # Use provided timezone or meeting's timezone
    display_timezone = timezone or meeting.timezone
    start_local = utc_to_local(meeting.start_time_utc, display_timezone)
    end_local = utc_to_local(meeting.end_time_utc, display_timezone)
    
    # Get participants
    from app.api.v1.schemas.meeting_schema import ParticipantResponse
    participants_data = []
    for participant in meeting.participants:
        participants_data.append(
            ParticipantResponse(
                id=participant.id,
                user_id=participant.user_id,
                user_name=participant.user.full_name if participant.user else "Unknown",
                user_email=participant.user.email if participant.user else "",
                role=participant.role,
                status=participant.status,
                created_at=participant.created_at
            )
        )
    
    # Get creator name
    creator_name = None
    if meeting.created_by:
        creator = db.query(User).filter(User.id == meeting.created_by).first()
        creator_name = creator.full_name if creator else None
    
    return MeetingResponse(
        id=meeting.id,
        company_id=meeting.company_id,
        title=meeting.title,
        description=meeting.description,
        meeting_link=meeting.meeting_link,
        meeting_platform=meeting.meeting_platform,
        start_time_utc=meeting.start_time_utc,
        end_time_utc=meeting.end_time_utc,
        start_time_local=start_local,
        end_time_local=end_local,
        timezone=meeting.timezone,
        created_by=meeting.created_by,
        creator_name=creator_name,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        participants=participants_data
    )


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    meeting_data: MeetingUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update a meeting.
    Only HOST or Admin can update.
    """
    logger.info(f"Updating meeting {meeting_id} by user {current_user.id}")
    
    meeting = MeetingService.update_meeting(
        db=db,
        company_id=current_user.company_id,
        meeting_id=meeting_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        data=meeting_data
    )
    
    # Convert to response format
    display_timezone = meeting_data.timezone or meeting.timezone
    start_local = utc_to_local(meeting.start_time_utc, display_timezone)
    end_local = utc_to_local(meeting.end_time_utc, display_timezone)
    
    # Get participants
    db.refresh(meeting)
    from app.api.v1.schemas.meeting_schema import ParticipantResponse
    participants_data = []
    for participant in meeting.participants:
        participants_data.append(
            ParticipantResponse(
                id=participant.id,
                user_id=participant.user_id,
                user_name=participant.user.full_name if participant.user else "Unknown",
                user_email=participant.user.email if participant.user else "",
                role=participant.role,
                status=participant.status,
                created_at=participant.created_at
            )
        )
    
    # Get creator name
    creator_name = None
    if meeting.created_by:
        creator = db.query(User).filter(User.id == meeting.created_by).first()
        creator_name = creator.full_name if creator else None
    
    # Emit WebSocket event
    try:
        from app.api.v1.services.websocket_service import websocket_service
        from app.api.v1.utils.websocket_helper import emit_websocket_event_async
        
        emit_websocket_event_async(
            websocket_service.emit_meeting_updated(
                db=db,
                tenant_id=current_user.company_id,
                meeting_id=meeting.id,
                meeting_title=meeting.title,
                updated_by=current_user.id,
                updated_by_name=current_user.full_name
            )
        )
    except Exception as e:
        logger.error(f"Failed to emit meeting_updated WebSocket event: {e}")
    
    return MeetingResponse(
        id=meeting.id,
        company_id=meeting.company_id,
        title=meeting.title,
        description=meeting.description,
        meeting_link=meeting.meeting_link,
        meeting_platform=meeting.meeting_platform,
        start_time_utc=meeting.start_time_utc,
        end_time_utc=meeting.end_time_utc,
        start_time_local=start_local,
        end_time_local=end_local,
        timezone=meeting.timezone,
        created_by=meeting.created_by,
        creator_name=creator_name,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        participants=participants_data
    )


@router.delete("/{meeting_id}", response_model=MessageResponse)
async def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a meeting.
    Only HOST or Admin can delete.
    """
    logger.info(f"Deleting meeting {meeting_id} by user {current_user.id}")
    
    # Get meeting title before deletion for WebSocket event
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.company_id == current_user.company_id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    meeting_title = meeting.title
    
    MeetingService.delete_meeting(
        db=db,
        company_id=current_user.company_id,
        meeting_id=meeting_id,
        user_id=current_user.id,
        user_role=current_user.role.value
    )
    
    # Emit WebSocket event
    try:
        from app.api.v1.services.websocket_service import websocket_service
        from app.api.v1.utils.websocket_helper import emit_websocket_event_async
        
        emit_websocket_event_async(
            websocket_service.emit_meeting_cancelled(
                db=db,
                tenant_id=current_user.company_id,
                meeting_id=meeting_id,
                meeting_title=meeting_title,
                cancelled_by=current_user.id,
                cancelled_by_name=current_user.full_name
            )
        )
    except Exception as e:
        logger.error(f"Failed to emit meeting_cancelled WebSocket event: {e}")
    
    return MessageResponse(message="Meeting deleted successfully")


@router.put("/{meeting_id}/participants/{user_id}/status", response_model=MessageResponse)
async def update_participant_status(
    meeting_id: int,
    user_id: int,
    status_data: ParticipantUpdate,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update participant status (accept/decline meeting invitation).
    Users can only update their own status.
    """
    # Users can only update their own status
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own participant status"
        )
    
    MeetingService.update_participant_status(
        db=db,
        company_id=current_user.company_id,
        meeting_id=meeting_id,
        user_id=user_id,
        status=status_data.status
    )
    
    return MessageResponse(message=f"Participant status updated to {status_data.status.value}")


# Note: Calendar routes have been moved to app/api/v1/routes/calendar.py
# Use GET /api/v1/calendar/day instead


@router.get("/calendar/month", response_model=CalendarMonthResponse)
async def get_calendar_month(
    year: int = Query(..., ge=2000, le=2100, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    timezone: str = Query(..., description="User's timezone (e.g., Asia/Kolkata)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all meetings for a month, grouped by date.
    Returns meetings where the user is a participant.
    """
    events_by_date = CalendarService.get_calendar_month(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        year=year,
        month=month,
        user_timezone=timezone
    )
    
    # Convert to response format
    calendar_days = []
    for date_str, events in sorted(events_by_date.items()):
        calendar_days.append(
            CalendarDayResponse(
                date=date_str,
                events=[
                    CalendarEventResponse(
                        meeting_id=e["meeting_id"],
                        title=e["title"],
                        start_time=e["start_time"],
                        end_time=e["end_time"],
                        timezone=e["timezone"],
                        meeting_link=e["meeting_link"],
                        meeting_platform=e["meeting_platform"],
                        participants_count=e["participants_count"]
                    )
                    for e in events
                ]
            )
        )
    
    return CalendarMonthResponse(
        year=year,
        month=month,
        events=calendar_days
    )

