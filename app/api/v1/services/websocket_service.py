"""
WebSocket Service
Service methods to trigger WebSocket events from business logic
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.api.v1.websocket.connection_manager import manager
from app.api.v1.websocket.redis_pubsub import redis_pubsub
from app.api.v1.websocket.event_handlers import event_handler
from app.api.v1.schemas.websocket_schema import (
    EventType,
    AttendanceMarkedEvent,
    TaskStatusUpdatedEvent,
    TaskAssignedEvent,
    LeaveAppliedEvent,
    LeaveApprovedEvent,
    EmployeeActivityEvent,
    DashboardUpdateEvent,
    MeetingCreatedEvent,
    MeetingUpdatedEvent,
    MeetingCancelledEvent,
    EventCreatedEvent,
    EventUpdatedEvent,
    EventCancelledEvent
)

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for triggering WebSocket events"""
    
    @staticmethod
    async def emit_attendance_marked(
        db: Session,
        tenant_id: int,
        employee_id: int,
        employee_name: str,
        action: str,  # LOGIN or LOGOUT
        attendance_summary: Optional[Dict[str, Any]] = None
    ):
        """Emit attendance marked event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "action": action,
                "attendance_summary": attendance_summary
            }
            
            await event_handler.handle_attendance_marked(event_data, db)
            logger.info(f"Attendance marked event emitted: {employee_name} - {action}")
            
        except Exception as e:
            logger.error(f"Error emitting attendance_marked event: {e}")
    
    @staticmethod
    async def emit_task_status_updated(
        db: Session,
        tenant_id: int,
        task_id: int,
        task_name: str,
        employee_name: str,
        new_status: str,
        old_status: Optional[str] = None,
        assigned_to_employee_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None
    ):
        """Emit task status updated event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "task_id": str(task_id),
                "task_name": task_name,
                "employee_name": employee_name,
                "new_status": new_status,
                "old_status": old_status,
                "assigned_to_employee_id": assigned_to_employee_id,
                "created_by_user_id": created_by_user_id
            }
            
            await event_handler.handle_task_status_updated(event_data, db)
            logger.info(f"Task status updated event emitted: {task_name} - {new_status}")
            
        except Exception as e:
            logger.error(f"Error emitting task_status_updated event: {e}")
    
    @staticmethod
    async def emit_task_assigned(
        db: Session,
        tenant_id: int,
        task_id: int,
        task_name: str,
        assigned_to: int,  # employee_id or user_id
        assigned_by: int,  # user_id
        assigned_by_name: Optional[str] = None
    ):
        """Emit task assigned event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "task_id": str(task_id),
                "task_name": task_name,
                "assigned_to": str(assigned_to),
                "assigned_by": str(assigned_by),
                "assigned_by_name": assigned_by_name
            }
            
            await event_handler.handle_task_assigned(event_data, db)
            logger.info(f"Task assigned event emitted: {task_name} to {assigned_to}")
            
        except Exception as e:
            logger.error(f"Error emitting task_assigned event: {e}")
    
    @staticmethod
    async def emit_employee_activity(
        db: Session,
        tenant_id: int,
        employee_id: int,
        employee_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Emit employee activity event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "action": action,
                "details": details
            }
            
            await event_handler.handle_employee_activity(event_data, db)
            logger.info(f"Employee activity event emitted: {employee_name} - {action}")
            
        except Exception as e:
            logger.error(f"Error emitting employee_activity event: {e}")
    
    @staticmethod
    async def emit_leave_applied(
        db: Session,
        tenant_id: int,
        leave_request_id: int,
        employee_id: int,
        employee_name: str,
        leave_type_name: str,
        start_date: str,
        end_date: str,
        number_of_days: int
    ):
        """Emit leave applied event (employee → admin)"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "leave_request_id": str(leave_request_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "leave_type_name": leave_type_name,
                "start_date": start_date,
                "end_date": end_date,
                "number_of_days": number_of_days
            }
            
            await event_handler.handle_leave_applied(event_data, db)
            logger.info(f"Leave applied event emitted: {employee_name} - {leave_type_name}")
            
        except Exception as e:
            logger.error(f"Error emitting leave_applied event: {e}")
    
    @staticmethod
    async def emit_leave_approved(
        db: Session,
        tenant_id: int,
        leave_request_id: int,
        employee_id: int,
        employee_name: str,
        leave_type_name: str,
        start_date: str,
        end_date: str,
        number_of_days: int,
        approved_by_name: str,
        approved: bool,
        rejection_reason: Optional[str] = None
    ):
        """Emit leave approved/rejected event (admin → employee)"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "leave_request_id": str(leave_request_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "leave_type_name": leave_type_name,
                "start_date": start_date,
                "end_date": end_date,
                "number_of_days": number_of_days,
                "approved_by_name": approved_by_name,
                "approved": approved,
                "rejection_reason": rejection_reason
            }
            
            await event_handler.handle_leave_approved(event_data, db)
            logger.info(f"Leave {'approved' if approved else 'rejected'} event emitted: {employee_name}")
            
        except Exception as e:
            logger.error(f"Error emitting leave_approved event: {e}")
    
    @staticmethod
    async def emit_dashboard_update(
        db: Session,
        tenant_id: int,
        update_type: str,
        data: Dict[str, Any]
    ):
        """Emit dashboard update event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "update_type": update_type,
                "data": data
            }
            
            await event_handler.handle_dashboard_update(event_data, db)
            logger.info(f"Dashboard update event emitted: {update_type}")
            
        except Exception as e:
            logger.error(f"Error emitting dashboard_update event: {e}")
    
    @staticmethod
    async def emit_meeting_created(
        db: Session,
        tenant_id: int,
        meeting_id: int,
        meeting_title: str,
        created_by: int,
        created_by_name: str
    ):
        """Emit meeting created event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "created_by": str(created_by),
                "created_by_name": created_by_name
            }
            
            await event_handler.handle_meeting_created(event_data, db)
            logger.info(f"Meeting created event emitted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error emitting meeting_created event: {e}")
    
    @staticmethod
    async def emit_meeting_updated(
        db: Session,
        tenant_id: int,
        meeting_id: int,
        meeting_title: str,
        updated_by: int,
        updated_by_name: str
    ):
        """Emit meeting updated event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "updated_by": str(updated_by),
                "updated_by_name": updated_by_name
            }
            
            await event_handler.handle_meeting_updated(event_data, db)
            logger.info(f"Meeting updated event emitted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error emitting meeting_updated event: {e}")
    
    @staticmethod
    async def emit_meeting_cancelled(
        db: Session,
        tenant_id: int,
        meeting_id: int,
        meeting_title: str,
        cancelled_by: int,
        cancelled_by_name: str
    ):
        """Emit meeting cancelled/deleted event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "cancelled_by": str(cancelled_by),
                "cancelled_by_name": cancelled_by_name
            }
            
            await event_handler.handle_meeting_cancelled(event_data, db)
            logger.info(f"Meeting cancelled event emitted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error emitting meeting_cancelled event: {e}")
    
    @staticmethod
    async def emit_event_created(
        db: Session,
        tenant_id: int,
        event_id: int,
        event_title: str,
        event_type: str,
        created_by: int,
        created_by_name: str
    ):
        """Emit event created event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "created_by": str(created_by),
                "created_by_name": created_by_name
            }
            
            await event_handler.handle_event_created(event_data, db)
            logger.info(f"Event created event emitted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error emitting event_created event: {e}")
    
    @staticmethod
    async def emit_event_updated(
        db: Session,
        tenant_id: int,
        event_id: int,
        event_title: str,
        event_type: str,
        updated_by: int,
        updated_by_name: str
    ):
        """Emit event updated event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "updated_by": str(updated_by),
                "updated_by_name": updated_by_name
            }
            
            await event_handler.handle_event_updated(event_data, db)
            logger.info(f"Event updated event emitted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error emitting event_updated event: {e}")
    
    @staticmethod
    async def emit_event_cancelled(
        db: Session,
        tenant_id: int,
        event_id: int,
        event_title: str,
        event_type: str,
        cancelled_by: int,
        cancelled_by_name: str
    ):
        """Emit event cancelled/deleted event"""
        try:
            event_data = {
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "cancelled_by": str(cancelled_by),
                "cancelled_by_name": cancelled_by_name
            }
            
            await event_handler.handle_event_cancelled(event_data, db)
            logger.info(f"Event cancelled event emitted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error emitting event_cancelled event: {e}")


# Global service instance
websocket_service = WebSocketService()

