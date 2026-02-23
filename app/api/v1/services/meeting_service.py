"""
Meeting Service for Calendar and Meeting Management
Handles CRUD operations, timezone conversions, and participant management
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime, date
import logging

from app.api.v1.models.meeting_model import (
    Meeting,
    MeetingParticipant,
    ParticipantRole,
    ParticipantStatus
)
from app.api.v1.models.user_model import User
from app.api.v1.models.company_model import Company
from app.api.v1.schemas.meeting_schema import MeetingCreate, MeetingUpdate
from app.api.v1.utils.timezone_utils import (
    local_to_utc,
    utc_to_local,
    validate_timezone
)
from app.api.v1.utils.error_handler import raise_http_exception
from app.api.v1.schemas.websocket_schema import SubscriptionPlan

logger = logging.getLogger(__name__)


def get_subscription_plan(db: Session, company_id: int) -> SubscriptionPlan:
    """
    Get subscription plan for a company.
    TODO: Implement actual subscription plan lookup from database
    For now, defaulting to PRO plan
    """
    # This should query the company's subscription plan from database
    # For now, returning PRO as default
    return SubscriptionPlan.PRO


def check_meeting_feature_access(db: Session, company_id: int, action: str = "create") -> None:
    """
    Check if company's subscription plan allows meeting features.
    
    Args:
        db: Database session
        company_id: Company ID
        action: Action being performed (create, update, delete)
    
    Raises:
        HTTPException if feature is not available
    """
    plan = get_subscription_plan(db, company_id)
    
    # Free Trial: Limited meetings (max 5 per month)
    if plan == SubscriptionPlan.BASIC:
        # Count meetings created this month
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        meeting_count = db.query(Meeting).filter(
            and_(
                Meeting.company_id == company_id,
                Meeting.created_at >= start_of_month
            )
        ).count()
        
        if meeting_count >= 5:
            raise_http_exception(
                message="Meeting limit reached. Upgrade to Basic plan for unlimited meetings.",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="MEETING_LIMIT_EXCEEDED"
            )
    
    # Basic and above: Unlimited meetings
    # Pro and Enterprise: Additional features (conflict detection, reminders, etc.)
    logger.debug(f"Meeting feature access granted for company {company_id}, plan: {plan.value}")


def check_meeting_overlap(
    db: Session,
    company_id: int,
    user_id: int,
    start_time_utc: datetime,
    end_time_utc: datetime,
    exclude_meeting_id: Optional[int] = None
) -> bool:
    """
    Check if a meeting overlaps with existing meetings for a user.
    Only for Pro and Enterprise plans.
    
    Args:
        db: Database session
        company_id: Company ID
        user_id: User ID to check overlaps for
        start_time_utc: Meeting start time (UTC)
        end_time_utc: Meeting end time (UTC)
        exclude_meeting_id: Meeting ID to exclude from check (for updates)
    
    Returns:
        True if overlap exists, False otherwise
    """
    plan = get_subscription_plan(db, company_id)
    
    # Only Pro and Enterprise plans have conflict detection
    if plan not in [SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE]:
        return False
    
    # Query for overlapping meetings where user is a participant
    query = db.query(Meeting).join(MeetingParticipant).filter(
        and_(
            Meeting.company_id == company_id,
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.status != ParticipantStatus.DECLINED,
            or_(
                # Meeting starts during existing meeting
                and_(
                    Meeting.start_time_utc <= start_time_utc,
                    Meeting.end_time_utc > start_time_utc
                ),
                # Meeting ends during existing meeting
                and_(
                    Meeting.start_time_utc < end_time_utc,
                    Meeting.end_time_utc >= end_time_utc
                ),
                # Meeting completely contains existing meeting
                and_(
                    Meeting.start_time_utc >= start_time_utc,
                    Meeting.end_time_utc <= end_time_utc
                )
            )
        )
    )
    
    if exclude_meeting_id:
        query = query.filter(Meeting.id != exclude_meeting_id)
    
    overlapping = query.first()
    return overlapping is not None


class MeetingService:
    """Service for meeting management operations"""
    
    @staticmethod
    def create_meeting(
        db: Session,
        company_id: int,
        creator_user_id: int,
        data: MeetingCreate
    ) -> Meeting:
        """
        Create a new meeting.
        
        Args:
            db: Database session
            company_id: Company ID
            creator_user_id: User ID creating the meeting
            data: Meeting creation data
        
        Returns:
            Created meeting
        """
        logger.info(f"Creating meeting: {data.title} for company {company_id}")
        
        # Check subscription feature access
        check_meeting_feature_access(db, company_id, "create")
        
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
        
        # Validate participants belong to same company
        if data.participants:
            participants = db.query(User).filter(
                and_(
                    User.id.in_(data.participants),
                    User.company_id == company_id,
                    User.is_active == True
                )
            ).all()
            
            if len(participants) != len(data.participants):
                raise_http_exception(
                    message="Some participants not found or belong to different company",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_PARTICIPANTS"
                )
        
        # Check for overlaps (Pro/Enterprise only)
        if check_meeting_overlap(db, company_id, creator_user_id, start_time_utc, end_time_utc):
            raise_http_exception(
                message="Meeting overlaps with an existing meeting",
                status_code=status.HTTP_409_CONFLICT,
                error_code="MEETING_OVERLAP"
            )
        
        # Create meeting
        meeting = Meeting(
            company_id=company_id,
            title=data.title,
            description=data.description,
            meeting_link=data.meeting_link,
            meeting_platform=data.meeting_platform,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            timezone=data.timezone,
            created_by=creator_user_id
        )
        db.add(meeting)
        db.flush()  # Get meeting ID
        
        # Add creator as HOST
        creator_participant = MeetingParticipant(
            meeting_id=meeting.id,
            company_id=company_id,
            user_id=creator_user_id,
            role=ParticipantRole.HOST,
            status=ParticipantStatus.ACCEPTED
        )
        db.add(creator_participant)
        
        # Add other participants
        for user_id in data.participants:
            if user_id != creator_user_id:  # Don't add creator twice
                participant = MeetingParticipant(
                    meeting_id=meeting.id,
                    company_id=company_id,
                    user_id=user_id,
                    role=ParticipantRole.PARTICIPANT,
                    status=ParticipantStatus.INVITED
                )
                db.add(participant)
        
        db.commit()
        db.refresh(meeting)
        
        logger.info(f"Meeting created successfully: {meeting.id}")
        return meeting
    
    @staticmethod
    def get_meeting_by_id(
        db: Session,
        company_id: int,
        meeting_id: int,
        user_timezone: Optional[str] = None
    ) -> Meeting:
        """
        Get meeting by ID with timezone conversion.
        
        Args:
            db: Database session
            company_id: Company ID
            meeting_id: Meeting ID
            user_timezone: User's timezone for display (optional)
        
        Returns:
            Meeting object
        """
        meeting = db.query(Meeting).options(
            joinedload(Meeting.participants).joinedload(MeetingParticipant.user)
        ).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.company_id == company_id
            )
        ).first()
        
        if not meeting:
            raise_http_exception(
                message="Meeting not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="MEETING_NOT_FOUND"
            )
        
        return meeting
    
    @staticmethod
    def update_meeting(
        db: Session,
        company_id: int,
        meeting_id: int,
        user_id: int,
        user_role: str,
        data: MeetingUpdate
    ) -> Meeting:
        """
        Update a meeting.
        Only HOST or Admin can update.
        
        Args:
            db: Database session
            company_id: Company ID
            meeting_id: Meeting ID
            user_id: User ID making the update
            user_role: User role (admin or employee)
            data: Update data
        
        Returns:
            Updated meeting
        """
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.company_id == company_id
            )
        ).first()
        
        if not meeting:
            raise_http_exception(
                message="Meeting not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="MEETING_NOT_FOUND"
            )
        
        # Check permissions: HOST or Admin only
        is_host = db.query(MeetingParticipant).filter(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.role == ParticipantRole.HOST
            )
        ).first() is not None
        
        is_admin = user_role == "admin" or user_id == meeting.created_by
        
        if not (is_host or is_admin):
            raise_http_exception(
                message="Only meeting host or admin can update this meeting",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="INSUFFICIENT_PERMISSIONS"
            )
        
        # Update fields
        if data.title is not None:
            meeting.title = data.title
        if data.description is not None:
            meeting.description = data.description
        if data.meeting_link is not None:
            meeting.meeting_link = data.meeting_link
        if data.meeting_platform is not None:
            meeting.meeting_platform = data.meeting_platform
        
        # Update times if provided
        if data.start_time is not None or data.end_time is not None or data.timezone is not None:
            timezone = data.timezone or meeting.timezone
            
            if not validate_timezone(timezone):
                raise_http_exception(
                    message=f"Invalid timezone: {timezone}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_TIMEZONE"
                )
            
            start_time = data.start_time if data.start_time else meeting.start_time_utc
            end_time = data.end_time if data.end_time else meeting.end_time_utc
            
            # Convert to UTC
            start_time_utc = local_to_utc(start_time, timezone)
            end_time_utc = local_to_utc(end_time, timezone)
            
            # Check for overlaps
            if check_meeting_overlap(db, company_id, user_id, start_time_utc, end_time_utc, exclude_meeting_id=meeting_id):
                raise_http_exception(
                    message="Updated meeting time overlaps with an existing meeting",
                    status_code=status.HTTP_409_CONFLICT,
                    error_code="MEETING_OVERLAP"
                )
            
            meeting.start_time_utc = start_time_utc
            meeting.end_time_utc = end_time_utc
            meeting.timezone = timezone
        
        # Update participants if provided
        if data.participants is not None:
            # Remove existing participants (except HOST)
            db.query(MeetingParticipant).filter(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.role != ParticipantRole.HOST
                )
            ).delete()
            
            # Add new participants
            for participant_user_id in data.participants:
                # Check if user belongs to company
                user = db.query(User).filter(
                    and_(
                        User.id == participant_user_id,
                        User.company_id == company_id,
                        User.is_active == True
                    )
                ).first()
                
                if not user:
                    continue
                
                # Check if already exists (as HOST)
                existing = db.query(MeetingParticipant).filter(
                    and_(
                        MeetingParticipant.meeting_id == meeting_id,
                        MeetingParticipant.user_id == participant_user_id
                    )
                ).first()
                
                if not existing:
                    participant = MeetingParticipant(
                        meeting_id=meeting_id,
                        company_id=company_id,
                        user_id=participant_user_id,
                        role=ParticipantRole.PARTICIPANT,
                        status=ParticipantStatus.INVITED
                    )
                    db.add(participant)
        
        db.commit()
        db.refresh(meeting)
        
        logger.info(f"Meeting updated: {meeting_id}")
        return meeting
    
    @staticmethod
    def delete_meeting(
        db: Session,
        company_id: int,
        meeting_id: int,
        user_id: int,
        user_role: str
    ) -> None:
        """
        Delete a meeting.
        Only HOST or Admin can delete.
        
        Args:
            db: Database session
            company_id: Company ID
            meeting_id: Meeting ID
            user_id: User ID making the delete
            user_role: User role
        """
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.company_id == company_id
            )
        ).first()
        
        if not meeting:
            raise_http_exception(
                message="Meeting not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="MEETING_NOT_FOUND"
            )
        
        # Check permissions: HOST or Admin only
        is_host = db.query(MeetingParticipant).filter(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.role == ParticipantRole.HOST
            )
        ).first() is not None
        
        is_admin = user_role == "admin" or user_id == meeting.created_by
        
        if not (is_host or is_admin):
            raise_http_exception(
                message="Only meeting host or admin can delete this meeting",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="INSUFFICIENT_PERMISSIONS"
            )
        
        db.delete(meeting)
        db.commit()
        
        logger.info(f"Meeting deleted: {meeting_id}")
    
    @staticmethod
    def update_participant_status(
        db: Session,
        company_id: int,
        meeting_id: int,
        user_id: int,
        status: ParticipantStatus
    ) -> MeetingParticipant:
        """
        Update participant status (accept/decline invitation).
        
        Args:
            db: Database session
            company_id: Company ID
            meeting_id: Meeting ID
            user_id: User ID
            status: New status
        
        Returns:
            Updated participant
        """
        participant = db.query(MeetingParticipant).filter(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.company_id == company_id
            )
        ).first()
        
        if not participant:
            raise_http_exception(
                message="Participant not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="PARTICIPANT_NOT_FOUND"
            )
        
        participant.status = status
        db.commit()
        db.refresh(participant)
        
        logger.info(f"Participant {user_id} status updated to {status.value} for meeting {meeting_id}")
        return participant

