"""
WebSocket Event Schemas for Real-time Communication
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SubscriptionPlan(str, Enum):
    """Subscription plan types"""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class EventType(str, Enum):
    """WebSocket event types"""
    ATTENDANCE_MARKED = "ATTENDANCE_MARKED"
    TASK_STATUS_UPDATED = "TASK_STATUS_UPDATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    LEAVE_APPLIED = "LEAVE_APPLIED"
    LEAVE_APPROVED = "LEAVE_APPROVED"
    LEAVE_REJECTED = "LEAVE_REJECTED"
    EMPLOYEE_ACTIVITY = "EMPLOYEE_ACTIVITY"
    DASHBOARD_UPDATE = "DASHBOARD_UPDATE"
    PING = "PING"
    PONG = "PONG"
    ERROR = "ERROR"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema"""
    event: EventType
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class AttendanceMarkedEvent(BaseModel):
    """Attendance marked event payload"""
    event: EventType = EventType.ATTENDANCE_MARKED
    tenant_id: str
    employee_id: str
    employee_name: str
    action: str  # LOGIN or LOGOUT
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attendance_summary: Optional[Dict[str, Any]] = None


class TaskStatusUpdatedEvent(BaseModel):
    """Task status updated event payload"""
    event: EventType = EventType.TASK_STATUS_UPDATED
    tenant_id: str
    task_id: str
    task_name: str
    employee_name: str
    new_status: str
    old_status: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskAssignedEvent(BaseModel):
    """Task assigned event payload"""
    event: EventType = EventType.TASK_ASSIGNED
    tenant_id: str
    task_id: str
    task_name: str
    assigned_to: str  # employee_id
    assigned_to_name: Optional[str] = None
    assigned_by: str  # user_id or name
    assigned_by_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmployeeActivityEvent(BaseModel):
    """Employee activity event payload"""
    event: EventType = EventType.EMPLOYEE_ACTIVITY
    tenant_id: str
    employee_id: str
    employee_name: str
    action: str  # UPDATED_PROFILE, CREATED_TASK, etc.
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LeaveAppliedEvent(BaseModel):
    """Leave applied event payload"""
    event: EventType = EventType.LEAVE_APPLIED
    tenant_id: str
    leave_request_id: str
    employee_id: str
    employee_name: str
    leave_type_name: str
    start_date: str
    end_date: str
    number_of_days: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LeaveApprovedEvent(BaseModel):
    """Leave approved/rejected event payload"""
    event: EventType  # LEAVE_APPROVED or LEAVE_REJECTED
    tenant_id: str
    leave_request_id: str
    employee_id: str
    employee_name: str
    leave_type_name: str
    start_date: str
    end_date: str
    number_of_days: int
    approved_by_name: str
    rejection_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DashboardUpdateEvent(BaseModel):
    """Dashboard update event payload"""
    event: EventType = EventType.DASHBOARD_UPDATE
    tenant_id: str
    update_type: str  # ATTENDANCE_STATS, TASK_STATS, etc.
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebSocketConnectionInfo(BaseModel):
    """Connection information for WebSocket client"""
    user_id: int
    tenant_id: int
    role: str
    subscription_plan: SubscriptionPlan
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    rooms: list[str] = Field(default_factory=list)


class WebSocketError(BaseModel):
    """WebSocket error message"""
    event: EventType = EventType.ERROR
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

