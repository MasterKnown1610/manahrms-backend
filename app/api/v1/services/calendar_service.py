"""
Calendar Service for Meeting Calendar Views
Handles date-based and month-based calendar queries with timezone conversion
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, date
from collections import defaultdict
import logging

from app.api.v1.models.meeting_model import Meeting, MeetingParticipant, ParticipantStatus
from app.api.v1.models.event_model import Event, EventParticipant, EventVisibility
from app.api.v1.services.event_service import check_event_visibility
from app.api.v1.utils.timezone_utils import (
    get_day_range_utc,
    get_month_range_utc,
    utc_to_local,
    format_time_for_display
)

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for calendar operations"""
    
    @staticmethod
    def get_calendar_day(
        db: Session,
        company_id: int,
        user_id: int,
        target_date: date,
        user_timezone: str
    ) -> List[Dict]:
        """
        Get all meetings for a specific day.
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID (to filter user's meetings)
            target_date: Target date
            user_timezone: User's timezone for display
        
        Returns:
            List of meeting dictionaries with local times
        """
        # Get start and end of day in UTC
        start_utc, end_utc = get_day_range_utc(target_date, user_timezone)
        
        # Query meetings where user is a participant
        meetings = db.query(Meeting).join(MeetingParticipant).filter(
            and_(
                Meeting.company_id == company_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.status != ParticipantStatus.DECLINED,
                Meeting.start_time_utc >= start_utc,
                Meeting.start_time_utc <= end_utc
            )
        ).options(
            joinedload(Meeting.participants).joinedload(MeetingParticipant.user)
        ).order_by(Meeting.start_time_utc).all()
        
        # Convert to response format
        events = []
        for meeting in meetings:
            # Convert UTC times to user's timezone
            start_local = utc_to_local(meeting.start_time_utc, user_timezone)
            end_local = utc_to_local(meeting.end_time_utc, user_timezone)
            
            events.append({
                "meeting_id": meeting.id,
                "title": meeting.title,
                "start_time": format_time_for_display(meeting.start_time_utc, user_timezone),
                "end_time": format_time_for_display(meeting.end_time_utc, user_timezone),
                "start_time_iso": start_local.isoformat(),
                "end_time_iso": end_local.isoformat(),
                "timezone": user_timezone,
                "meeting_link": meeting.meeting_link,
                "meeting_platform": meeting.meeting_platform.value,
                "participants_count": len(meeting.participants),
                "description": meeting.description
            })
        
        logger.debug(f"Found {len(events)} meetings for date {target_date} in timezone {user_timezone}")
        return events
    
    @staticmethod
    def get_calendar_month(
        db: Session,
        company_id: int,
        user_id: int,
        year: int,
        month: int,
        user_timezone: str
    ) -> Dict[str, List[Dict]]:
        """
        Get all meetings for a month, grouped by date.
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            year: Year
            month: Month (1-12)
            user_timezone: User's timezone
        
        Returns:
            Dictionary with date strings as keys and lists of meetings as values
        """
        # Get start and end of month in UTC
        start_utc, end_utc = get_month_range_utc(year, month, user_timezone)
        
        # Query meetings where user is a participant
        meetings = db.query(Meeting).join(MeetingParticipant).filter(
            and_(
                Meeting.company_id == company_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.status != ParticipantStatus.DECLINED,
                Meeting.start_time_utc >= start_utc,
                Meeting.start_time_utc <= end_utc
            )
        ).options(
            joinedload(Meeting.participants).joinedload(MeetingParticipant.user)
        ).order_by(Meeting.start_time_utc).all()
        
        # Group by date
        events_by_date = defaultdict(list)
        
        for meeting in meetings:
            # Convert UTC to user's timezone to get the date
            start_local = utc_to_local(meeting.start_time_utc, user_timezone)
            date_key = start_local.date().isoformat()
            
            events_by_date[date_key].append({
                "meeting_id": meeting.id,
                "title": meeting.title,
                "start_time": format_time_for_display(meeting.start_time_utc, user_timezone),
                "end_time": format_time_for_display(meeting.end_time_utc, user_timezone),
                "start_time_iso": start_local.isoformat(),
                "end_time_iso": utc_to_local(meeting.end_time_utc, user_timezone).isoformat(),
                "timezone": user_timezone,
                "meeting_link": meeting.meeting_link,
                "meeting_platform": meeting.meeting_platform.value,
                "participants_count": len(meeting.participants),
                "description": meeting.description
            })
        
        logger.debug(f"Found meetings for {year}-{month} in timezone {user_timezone}: {len(meetings)} total")
        return dict(events_by_date)
    
    @staticmethod
    def get_events_for_month(
        db: Session,
        company_id: int,
        user_id: int,
        user_department_id: Optional[int],
        year: int,
        month: int,
        user_timezone: str
    ) -> Dict[str, List[Dict]]:
        """
        Get all events for a month, grouped by date (with visibility filtering).
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            user_department_id: User's department ID
            year: Year
            month: Month (1-12)
            user_timezone: User's timezone
        
        Returns:
            Dictionary with date strings as keys and lists of events as values
        """
        # Get start and end of month in UTC
        start_utc, end_utc = get_month_range_utc(year, month, user_timezone)
        
        # Query events for the company
        events = db.query(Event).filter(
            and_(
                Event.company_id == company_id,
                Event.start_time_utc >= start_utc,
                Event.start_time_utc <= end_utc
            )
        ).options(
            joinedload(Event.participants).joinedload(EventParticipant.user),
            joinedload(Event.department)
        ).order_by(Event.start_time_utc).all()
        
        # Filter by visibility
        visible_events = []
        for event in events:
            if check_event_visibility(db, event, user_id, user_department_id):
                visible_events.append(event)
        
        # Group by date
        events_by_date = defaultdict(list)
        
        for event in visible_events:
            # Convert UTC to user's timezone to get the date
            start_local = utc_to_local(event.start_time_utc, user_timezone)
            date_key = start_local.date().isoformat()
            
            events_by_date[date_key].append({
                "event_id": event.id,
                "title": event.title,
                "start_time": format_time_for_display(event.start_time_utc, user_timezone) if not event.is_all_day else "All Day",
                "end_time": format_time_for_display(event.end_time_utc, user_timezone) if not event.is_all_day else "All Day",
                "start_time_iso": start_local.isoformat(),
                "end_time_iso": utc_to_local(event.end_time_utc, user_timezone).isoformat(),
                "timezone": user_timezone,
                "event_type": event.event_type.value,
                "location": event.location,
                "is_all_day": event.is_all_day,
                "description": event.description
            })
        
        logger.debug(f"Found events for {year}-{month} in timezone {user_timezone}: {len(visible_events)} total")
        return dict(events_by_date)
    
    @staticmethod
    def get_unified_calendar_month(
        db: Session,
        company_id: int,
        user_id: int,
        user_department_id: Optional[int],
        year: int,
        month: int,
        user_timezone: str
    ) -> Dict[str, Dict]:
        """
        Get unified calendar month view with both meetings and events.
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            user_department_id: User's department ID
            year: Year
            month: Month (1-12)
            user_timezone: User's timezone
        
        Returns:
            Dictionary with date strings as keys and dictionaries with meetings/events lists as values
        """
        # Get meetings for the month
        meetings_by_date = CalendarService.get_calendar_month(
            db=db,
            company_id=company_id,
            user_id=user_id,
            year=year,
            month=month,
            user_timezone=user_timezone
        )
        
        # Get events for the month
        events_by_date = CalendarService.get_events_for_month(
            db=db,
            company_id=company_id,
            user_id=user_id,
            user_department_id=user_department_id,
            year=year,
            month=month,
            user_timezone=user_timezone
        )
        
        # Get all unique dates
        all_dates = set(list(meetings_by_date.keys()) + list(events_by_date.keys()))
        
        # Combine meetings and events by date
        unified_calendar = {}
        for date_str in sorted(all_dates):
            # Convert meetings to unified format
            meeting_items = []
            if date_str in meetings_by_date:
                for meeting in meetings_by_date[date_str]:
                    meeting_items.append({
                        "id": meeting["meeting_id"],
                        "title": meeting["title"],
                        "start_time": meeting["start_time"],
                        "end_time": meeting["end_time"],
                        "start_time_iso": meeting["start_time_iso"],
                        "end_time_iso": meeting["end_time_iso"],
                        "timezone": meeting["timezone"],
                        "type": "MEETING",
                        "location": None,
                        "is_all_day": False,
                        "description": meeting.get("description")
                    })
            
            # Convert events to unified format
            event_items = []
            if date_str in events_by_date:
                for event in events_by_date[date_str]:
                    event_items.append({
                        "id": event["event_id"],
                        "title": event["title"],
                        "start_time": event["start_time"],
                        "end_time": event["end_time"],
                        "start_time_iso": event["start_time_iso"],
                        "end_time_iso": event["end_time_iso"],
                        "timezone": event["timezone"],
                        "type": event["event_type"],
                        "location": event.get("location"),
                        "is_all_day": event["is_all_day"],
                        "description": event.get("description")
                    })
            
            unified_calendar[date_str] = {
                "meetings": meeting_items,
                "events": event_items
            }
        
        return unified_calendar
    
    @staticmethod
    def get_user_meetings(
        db: Session,
        company_id: int,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Meeting]:
        """
        Get all meetings for a user within a date range.
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            start_date: Start date (optional, defaults to now)
            end_date: End date (optional)
        
        Returns:
            List of Meeting objects
        """
        if start_date is None:
            start_date = datetime.utcnow()
        
        query = db.query(Meeting).join(MeetingParticipant).filter(
            and_(
                Meeting.company_id == company_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.status != ParticipantStatus.DECLINED,
                Meeting.start_time_utc >= start_date
            )
        )
        
        if end_date:
            query = query.filter(Meeting.start_time_utc <= end_date)
        
        return query.options(
            joinedload(Meeting.participants).joinedload(MeetingParticipant.user)
        ).order_by(Meeting.start_time_utc).all()
    
    @staticmethod
    def get_events_for_day(
        db: Session,
        company_id: int,
        user_id: int,
        user_department_id: Optional[int],
        target_date: date,
        user_timezone: str
    ) -> List[Dict]:
        """
        Get all events for a specific day (with visibility filtering).
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            user_department_id: User's department ID
            target_date: Target date
            user_timezone: User's timezone for display
        
        Returns:
            List of event dictionaries with local times
        """
        # Get start and end of day in UTC
        start_utc, end_utc = get_day_range_utc(target_date, user_timezone)
        
        # Query events for the company
        events = db.query(Event).filter(
            and_(
                Event.company_id == company_id,
                Event.start_time_utc >= start_utc,
                Event.start_time_utc <= end_utc
            )
        ).options(
            joinedload(Event.participants).joinedload(EventParticipant.user),
            joinedload(Event.department)
        ).order_by(Event.start_time_utc).all()
        
        # Filter by visibility
        visible_events = []
        for event in events:
            if check_event_visibility(db, event, user_id, user_department_id):
                visible_events.append(event)
        
        # Convert to response format
        event_list = []
        for event in visible_events:
            # Convert UTC times to user's timezone
            start_local = utc_to_local(event.start_time_utc, user_timezone)
            end_local = utc_to_local(event.end_time_utc, user_timezone)
            
            event_list.append({
                "event_id": event.id,
                "title": event.title,
                "start_time": format_time_for_display(event.start_time_utc, user_timezone) if not event.is_all_day else "All Day",
                "end_time": format_time_for_display(event.end_time_utc, user_timezone) if not event.is_all_day else "All Day",
                "start_time_iso": start_local.isoformat(),
                "end_time_iso": end_local.isoformat(),
                "timezone": user_timezone,
                "event_type": event.event_type.value,
                "location": event.location,
                "is_all_day": event.is_all_day,
                "description": event.description
            })
        
        logger.debug(f"Found {len(event_list)} events for date {target_date} in timezone {user_timezone}")
        return event_list
    
    @staticmethod
    def get_unified_calendar_day(
        db: Session,
        company_id: int,
        user_id: int,
        user_department_id: Optional[int],
        target_date: date,
        user_timezone: str
    ) -> Dict:
        """
        Get unified calendar day view with both meetings and events.
        
        Args:
            db: Database session
            company_id: Company ID
            user_id: User ID
            user_department_id: User's department ID
            target_date: Target date
            user_timezone: User's timezone
        
        Returns:
            Dictionary with meetings and events lists
        """
        # Get meetings
        meetings = CalendarService.get_calendar_day(
            db=db,
            company_id=company_id,
            user_id=user_id,
            target_date=target_date,
            user_timezone=user_timezone
        )
        
        # Get events
        events = CalendarService.get_events_for_day(
            db=db,
            company_id=company_id,
            user_id=user_id,
            user_department_id=user_department_id,
            target_date=target_date,
            user_timezone=user_timezone
        )
        
        # Convert to unified format
        meeting_items = []
        for meeting in meetings:
            meeting_items.append({
                "id": meeting["meeting_id"],
                "title": meeting["title"],
                "start_time": meeting["start_time"],
                "end_time": meeting["end_time"],
                "start_time_iso": meeting["start_time_iso"],
                "end_time_iso": meeting["end_time_iso"],
                "timezone": meeting["timezone"],
                "type": "MEETING",
                "location": None,
                "is_all_day": False,
                "description": meeting.get("description")
            })
        
        event_items = []
        for event in events:
            event_items.append({
                "id": event["event_id"],
                "title": event["title"],
                "start_time": event["start_time"],
                "end_time": event["end_time"],
                "start_time_iso": event["start_time_iso"],
                "end_time_iso": event["end_time_iso"],
                "timezone": event["timezone"],
                "type": event["event_type"],
                "location": event.get("location"),
                "is_all_day": event["is_all_day"],
                "description": event.get("description")
            })
        
        return {
            "meetings": meeting_items,
            "events": event_items
        }

