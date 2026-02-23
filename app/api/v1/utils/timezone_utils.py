"""
Timezone utility functions for calendar and meeting management.
Handles conversion between local time and UTC for multi-timezone support.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
import pytz

logger = logging.getLogger(__name__)

# Common timezones list for dropdown
COMMON_TIMEZONES = [
    "Asia/Kolkata",
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Dubai",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Australia/Melbourne",
    "America/Toronto",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "Africa/Cairo",
    "Africa/Johannesburg",
]


def get_all_timezones() -> list[str]:
    """
    Get all available IANA timezones.
    Returns a sorted list of all timezone identifiers.
    """
    try:
        # Use zoneinfo (Python 3.9+) if available, fallback to pytz
        if hasattr(ZoneInfo, 'available_timezones'):
            return sorted(ZoneInfo.available_timezones())
        else:
            return sorted(pytz.all_timezones)
    except Exception as e:
        logger.error(f"Error getting timezones: {e}")
        # Fallback to common timezones
        return COMMON_TIMEZONES


def get_common_timezones() -> list[str]:
    """
    Get list of common timezones for dropdown.
    Returns a curated list of frequently used timezones.
    """
    return COMMON_TIMEZONES


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate if a timezone string is a valid IANA timezone.
    
    Args:
        timezone_str: Timezone string to validate (e.g., "Asia/Kolkata")
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to create a ZoneInfo object
        ZoneInfo(timezone_str)
        return True
    except Exception:
        try:
            # Fallback to pytz
            pytz.timezone(timezone_str)
            return True
        except Exception:
            return False


def local_to_utc(local_time: datetime, timezone_str: str) -> datetime:
    """
    Convert local time to UTC.
    
    Args:
        local_time: Local datetime (naive or timezone-aware)
        timezone_str: IANA timezone string (e.g., "Asia/Kolkata")
    
    Returns:
        UTC datetime (timezone-aware)
    
    Raises:
        ValueError: If timezone is invalid
    """
    if not validate_timezone(timezone_str):
        raise ValueError(f"Invalid timezone: {timezone_str}")
    
    try:
        # Use zoneinfo (Python 3.9+)
        tz = ZoneInfo(timezone_str)
    except Exception:
        # Fallback to pytz
        tz = pytz.timezone(timezone_str)
    
    # If local_time is naive, assume it's in the given timezone
    if local_time.tzinfo is None:
        local_time = tz.localize(local_time)
    else:
        # Convert to the target timezone first
        local_time = local_time.astimezone(tz)
    
    # Convert to UTC
    utc_time = local_time.astimezone(ZoneInfo("UTC"))
    return utc_time


def utc_to_local(utc_time: datetime, timezone_str: str) -> datetime:
    """
    Convert UTC time to local timezone.
    
    Args:
        utc_time: UTC datetime (naive or timezone-aware)
        timezone_str: Target IANA timezone string (e.g., "Asia/Kolkata")
    
    Returns:
        Local datetime (timezone-aware)
    
    Raises:
        ValueError: If timezone is invalid
    """
    if not validate_timezone(timezone_str):
        raise ValueError(f"Invalid timezone: {timezone_str}")
    
    try:
        # Use zoneinfo (Python 3.9+)
        tz = ZoneInfo(timezone_str)
    except Exception:
        # Fallback to pytz
        tz = pytz.timezone(timezone_str)
    
    # If utc_time is naive, assume it's UTC
    if utc_time.tzinfo is None:
        utc_time = ZoneInfo("UTC").localize(utc_time)
    else:
        # Ensure it's in UTC
        utc_time = utc_time.astimezone(ZoneInfo("UTC"))
    
    # Convert to local timezone
    local_time = utc_time.astimezone(tz)
    return local_time


def get_day_range_utc(date: datetime, timezone_str: str) -> Tuple[datetime, datetime]:
    """
    Get start and end of day in UTC for a given date in a timezone.
    
    Args:
        date: Date to get range for (can be datetime or date)
        timezone_str: IANA timezone string
    
    Returns:
        Tuple of (start_of_day_utc, end_of_day_utc)
    """
    if not validate_timezone(timezone_str):
        raise ValueError(f"Invalid timezone: {timezone_str}")
    
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = pytz.timezone(timezone_str)
    
    # If date is a datetime, extract just the date part
    if isinstance(date, datetime):
        date_only = date.date()
    else:
        date_only = date
    
    # Create start of day in local timezone
    start_local = tz.localize(datetime.combine(date_only, datetime.min.time()))
    # Create end of day in local timezone (23:59:59.999999)
    end_local = tz.localize(datetime.combine(date_only, datetime.max.time().replace(microsecond=0)))
    
    # Convert to UTC
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_local.astimezone(ZoneInfo("UTC"))
    
    return start_utc, end_utc


def get_month_range_utc(year: int, month: int, timezone_str: str) -> Tuple[datetime, datetime]:
    """
    Get start and end of month in UTC for a given year/month in a timezone.
    
    Args:
        year: Year
        month: Month (1-12)
        timezone_str: IANA timezone string
    
    Returns:
        Tuple of (start_of_month_utc, end_of_month_utc)
    """
    from calendar import monthrange
    
    if not validate_timezone(timezone_str):
        raise ValueError(f"Invalid timezone: {timezone_str}")
    
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = pytz.timezone(timezone_str)
    
    # Get first and last day of month
    first_day = datetime(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num)
    
    # Get day ranges
    start_utc, _ = get_day_range_utc(first_day, timezone_str)
    _, end_utc = get_day_range_utc(last_day, timezone_str)
    
    return start_utc, end_utc


def format_time_for_display(dt: datetime, timezone_str: str, format_str: str = "%I:%M %p") -> str:
    """
    Format datetime for display in a specific timezone.
    
    Args:
        dt: UTC datetime
        timezone_str: Target timezone
        format_str: strftime format string
    
    Returns:
        Formatted time string
    """
    local_time = utc_to_local(dt, timezone_str)
    return local_time.strftime(format_str)

