"""
WebSocket Event Handlers
Handles business logic for different event types
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.api.v1.websocket.connection_manager import manager
from app.api.v1.websocket.redis_pubsub import redis_pubsub
from app.api.v1.schemas.websocket_schema import (
    EventType,
    AttendanceMarkedEvent,
    TaskStatusUpdatedEvent,
    TaskAssignedEvent,
    EmployeeActivityEvent,
    DashboardUpdateEvent,
    SubscriptionPlan
)

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles WebSocket events and broadcasts"""
    
    @staticmethod
    async def handle_attendance_marked(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle ATTENDANCE_MARKED event
        Broadcasts to: Admin, HR, Manager roles
        """
        try:
            tenant_id = event_data.get('tenant_id')
            employee_id = event_data.get('employee_id')
            employee_name = event_data.get('employee_name', 'Employee')
            action = event_data.get('action', 'LOGIN')
            
            # Create message
            message = {
                "event": EventType.ATTENDANCE_MARKED.value,
                "tenant_id": str(tenant_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"{employee_name} marked attendance ({action})",
                "attendance_summary": event_data.get('attendance_summary')
            }
            
            # Broadcast to roles that should receive attendance updates
            roles_to_notify = ['ADMIN', 'HR', 'MANAGER']
            
            for role in roles_to_notify:
                await manager.broadcast_to_role(
                    tenant_id=int(tenant_id),
                    role=role,
                    message=message,
                    exclude_connection_id=connection_id
                )
            
            # Also publish to Redis for other instances
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Attendance marked event broadcasted: {employee_name} - {action}")
            
        except Exception as e:
            logger.error(f"Error handling attendance_marked event: {e}")
    
    @staticmethod
    async def handle_task_status_updated(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle TASK_STATUS_UPDATED event
        Broadcasts to: Assigned Manager, Admin, Task Creator
        """
        try:
            tenant_id = event_data.get('tenant_id')
            task_id = event_data.get('task_id')
            task_name = event_data.get('task_name', 'Task')
            employee_name = event_data.get('employee_name', 'Employee')
            new_status = event_data.get('new_status')
            assigned_to = event_data.get('assigned_to_employee_id')
            created_by = event_data.get('created_by_user_id')
            
            message = {
                "event": EventType.TASK_STATUS_UPDATED.value,
                "tenant_id": str(tenant_id),
                "task_id": str(task_id),
                "task_name": task_name,
                "employee_name": employee_name,
                "new_status": new_status,
                "old_status": event_data.get('old_status'),
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"{employee_name} updated task '{task_name}' to {new_status}"
            }
            
            # If employee updated, notify admin
            # If admin updated, notify assigned employee
            from app.api.v1.models.user_model import User
            
            # Check who updated (if created_by is provided, we can infer)
            # For now, always notify admin and assigned employee
            await manager.broadcast_to_role(
                tenant_id=int(tenant_id),
                role='ADMIN',
                message=message,
                exclude_connection_id=connection_id
            )
            
            # Send to assigned employee if task is assigned
            if assigned_to:
                assigned_user = db.query(User).filter(
                    User.employee_id == int(assigned_to),
                    User.company_id == int(tenant_id)
                ).first()
                if assigned_user:
                    await manager.send_to_user(
                        tenant_id=int(tenant_id),
                        user_id=assigned_user.id,
                        message=message
                    )
            
            # Send to task creator if different from updater
            if created_by:
                await manager.send_to_user(
                    tenant_id=int(tenant_id),
                    user_id=int(created_by),
                    message=message
                )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Task status updated event broadcasted: {task_name} - {new_status}")
            
        except Exception as e:
            logger.error(f"Error handling task_status_updated event: {e}")
    
    @staticmethod
    async def handle_task_assigned(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle TASK_ASSIGNED event
        Broadcasts to: Assigned Employee
        """
        try:
            tenant_id = event_data.get('tenant_id')
            task_id = event_data.get('task_id')
            task_name = event_data.get('task_name', 'Task')
            assigned_to = event_data.get('assigned_to')
            assigned_by_name = event_data.get('assigned_by_name', 'Admin')
            
            message = {
                "event": EventType.TASK_ASSIGNED.value,
                "tenant_id": str(tenant_id),
                "task_id": str(task_id),
                "task_name": task_name,
                "assigned_to": str(assigned_to),
                "assigned_by": event_data.get('assigned_by'),
                "assigned_by_name": assigned_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"New task assigned: {task_name}"
            }
            
            # Send to assigned employee
            await manager.send_to_user(
                tenant_id=int(tenant_id),
                user_id=int(assigned_to),
                message=message
            )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_user_channel(int(tenant_id), int(assigned_to))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Task assigned event sent: {task_name} to user {assigned_to}")
            
        except Exception as e:
            logger.error(f"Error handling task_assigned event: {e}")
    
    @staticmethod
    async def handle_employee_activity(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle EMPLOYEE_ACTIVITY event
        Broadcasts based on subscription plan
        """
        try:
            tenant_id = event_data.get('tenant_id')
            employee_id = event_data.get('employee_id')
            employee_name = event_data.get('employee_name', 'Employee')
            action = event_data.get('action')
            
            message = {
                "event": EventType.EMPLOYEE_ACTIVITY.value,
                "tenant_id": str(tenant_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "action": action,
                "details": event_data.get('details'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Only broadcast to Enterprise plan subscribers
            # This is handled at the connection level based on subscription_plan
            
            # Broadcast to Admin (they always get activity updates)
            await manager.broadcast_to_role(
                tenant_id=int(tenant_id),
                role='ADMIN',
                message=message,
                exclude_connection_id=connection_id
            )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Employee activity event broadcasted: {employee_name} - {action}")
            
        except Exception as e:
            logger.error(f"Error handling employee_activity event: {e}")
    
    @staticmethod
    async def handle_dashboard_update(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle DASHBOARD_UPDATE event
        Broadcasts to: Admin, HR (based on subscription)
        """
        try:
            tenant_id = event_data.get('tenant_id')
            update_type = event_data.get('update_type')
            
            message = {
                "event": EventType.DASHBOARD_UPDATE.value,
                "tenant_id": str(tenant_id),
                "update_type": update_type,
                "data": event_data.get('data', {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to Admin and HR
            for role in ['ADMIN', 'HR']:
                await manager.broadcast_to_role(
                    tenant_id=int(tenant_id),
                    role=role,
                    message=message,
                    exclude_connection_id=connection_id
                )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Dashboard update event broadcasted: {update_type}")
            
        except Exception as e:
            logger.error(f"Error handling dashboard_update event: {e}")
    
    @staticmethod
    async def handle_leave_applied(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle LEAVE_APPLIED event
        Broadcasts to: Admin, HR (employee applied for leave)
        """
        try:
            tenant_id = event_data.get('tenant_id')
            leave_request_id = event_data.get('leave_request_id')
            employee_name = event_data.get('employee_name')
            leave_type_name = event_data.get('leave_type_name')
            number_of_days = event_data.get('number_of_days')
            
            message = {
                "event": EventType.LEAVE_APPLIED.value,
                "tenant_id": str(tenant_id),
                "leave_request_id": str(leave_request_id),
                "employee_id": event_data.get('employee_id'),
                "employee_name": employee_name,
                "leave_type_name": leave_type_name,
                "start_date": event_data.get('start_date'),
                "end_date": event_data.get('end_date'),
                "number_of_days": number_of_days,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"{employee_name} applied for {number_of_days} day(s) of {leave_type_name} leave"
            }
            
            # Broadcast to Admin and HR
            for role in ['ADMIN', 'HR']:
                await manager.broadcast_to_role(
                    tenant_id=int(tenant_id),
                    role=role,
                    message=message,
                    exclude_connection_id=connection_id
                )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Leave applied event broadcasted: {employee_name} - {leave_type_name}")
            
        except Exception as e:
            logger.error(f"Error handling leave_applied event: {e}")
    
    @staticmethod
    async def handle_leave_approved(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle LEAVE_APPROVED/LEAVE_REJECTED event
        Broadcasts to: Assigned Employee (admin approved/rejected leave)
        """
        try:
            tenant_id = event_data.get('tenant_id')
            leave_request_id = event_data.get('leave_request_id')
            employee_id = event_data.get('employee_id')
            employee_name = event_data.get('employee_name')
            leave_type_name = event_data.get('leave_type_name')
            approved = event_data.get('approved', True)
            approved_by_name = event_data.get('approved_by_name', 'Admin')
            
            event_type = EventType.LEAVE_APPROVED.value if approved else EventType.LEAVE_REJECTED.value
            status_text = "approved" if approved else "rejected"
            
            message = {
                "event": event_type,
                "tenant_id": str(tenant_id),
                "leave_request_id": str(leave_request_id),
                "employee_id": str(employee_id),
                "employee_name": employee_name,
                "leave_type_name": leave_type_name,
                "start_date": event_data.get('start_date'),
                "end_date": event_data.get('end_date'),
                "number_of_days": event_data.get('number_of_days'),
                "approved_by_name": approved_by_name,
                "rejection_reason": event_data.get('rejection_reason'),
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Your {leave_type_name} leave request has been {status_text} by {approved_by_name}"
            }
            
            # Get user_id from employee_id
            from app.api.v1.models.user_model import User
            assigned_user = db.query(User).filter(
                User.employee_id == int(employee_id),
                User.company_id == int(tenant_id)
            ).first()
            
            if assigned_user:
                # Send to employee
                await manager.send_to_user(
                    tenant_id=int(tenant_id),
                    user_id=assigned_user.id,
                    message=message
                )
                
                # Publish to Redis
                if redis_pubsub.is_connected:
                    channel = redis_pubsub.get_user_channel(int(tenant_id), assigned_user.id)
                    await redis_pubsub.publish(channel, message)
                
                logger.info(f"Leave {status_text} event sent: {employee_name}")
            else:
                logger.warning(f"Leave {status_text} event: No user found for employee {employee_id}")
            
        except Exception as e:
            logger.error(f"Error handling leave_approved event: {e}")
    
    @staticmethod
    async def handle_meeting_created(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle MEETING_CREATED event
        Broadcasts to: All meeting participants
        """
        try:
            tenant_id = event_data.get('tenant_id')
            meeting_id = event_data.get('meeting_id')
            meeting_title = event_data.get('meeting_title')
            created_by = event_data.get('created_by')
            created_by_name = event_data.get('created_by_name', 'Admin')
            
            message = {
                "event": EventType.MEETING_CREATED.value,
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "created_by": str(created_by),
                "created_by_name": created_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"New meeting created: {meeting_title}"
            }
            
            # Broadcast to all participants of the meeting
            # Get meeting participants from database
            from app.api.v1.models.meeting_model import Meeting, MeetingParticipant
            
            meeting = db.query(Meeting).filter(Meeting.id == int(meeting_id)).first()
            if meeting:
                participants = db.query(MeetingParticipant).filter(
                    MeetingParticipant.meeting_id == int(meeting_id)
                ).all()
                
                for participant in participants:
                    await manager.send_to_user(
                        tenant_id=int(tenant_id),
                        user_id=participant.user_id,
                        message=message
                    )
            
            # Also broadcast to tenant (for admin visibility)
            await manager.broadcast_to_tenant(
                tenant_id=int(tenant_id),
                message=message,
                exclude_connection_id=connection_id
            )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Meeting created event broadcasted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error handling meeting_created event: {e}")
    
    @staticmethod
    async def handle_meeting_updated(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle MEETING_UPDATED event
        Broadcasts to: All meeting participants
        """
        try:
            tenant_id = event_data.get('tenant_id')
            meeting_id = event_data.get('meeting_id')
            meeting_title = event_data.get('meeting_title')
            updated_by = event_data.get('updated_by')
            updated_by_name = event_data.get('updated_by_name', 'Admin')
            
            message = {
                "event": EventType.MEETING_UPDATED.value,
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "updated_by": str(updated_by),
                "updated_by_name": updated_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Meeting updated: {meeting_title}"
            }
            
            # Broadcast to all participants
            from app.api.v1.models.meeting_model import MeetingParticipant
            
            participants = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == int(meeting_id)
            ).all()
            
            for participant in participants:
                await manager.send_to_user(
                    tenant_id=int(tenant_id),
                    user_id=participant.user_id,
                    message=message
                )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Meeting updated event broadcasted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error handling meeting_updated event: {e}")
    
    @staticmethod
    async def handle_meeting_cancelled(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle MEETING_CANCELLED event
        Broadcasts to: All meeting participants
        """
        try:
            tenant_id = event_data.get('tenant_id')
            meeting_id = event_data.get('meeting_id')
            meeting_title = event_data.get('meeting_title')
            cancelled_by = event_data.get('cancelled_by')
            cancelled_by_name = event_data.get('cancelled_by_name', 'Admin')
            
            message = {
                "event": EventType.MEETING_CANCELLED.value,
                "tenant_id": str(tenant_id),
                "meeting_id": str(meeting_id),
                "meeting_title": meeting_title,
                "cancelled_by": str(cancelled_by),
                "cancelled_by_name": cancelled_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Meeting cancelled: {meeting_title}"
            }
            
            # Broadcast to all participants (if meeting still exists in DB)
            # Note: Meeting might be deleted, so we try to get participants first
            from app.api.v1.models.meeting_model import MeetingParticipant
            
            try:
                participants = db.query(MeetingParticipant).filter(
                    MeetingParticipant.meeting_id == int(meeting_id)
                ).all()
                
                for participant in participants:
                    await manager.send_to_user(
                        tenant_id=int(tenant_id),
                        user_id=participant.user_id,
                        message=message
                    )
            except Exception:
                # Meeting already deleted, broadcast to tenant
                pass
            
            # Broadcast to tenant
            await manager.broadcast_to_tenant(
                tenant_id=int(tenant_id),
                message=message,
                exclude_connection_id=connection_id
            )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Meeting cancelled event broadcasted: {meeting_title}")
            
        except Exception as e:
            logger.error(f"Error handling meeting_cancelled event: {e}")
    
    @staticmethod
    async def handle_event_created(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle EVENT_CREATED event
        Broadcasts to: All users based on event visibility
        """
        try:
            tenant_id = event_data.get('tenant_id')
            event_id = event_data.get('event_id')
            event_title = event_data.get('event_title')
            event_type = event_data.get('event_type')
            created_by = event_data.get('created_by')
            created_by_name = event_data.get('created_by_name', 'Admin')
            
            message = {
                "event": EventType.EVENT_CREATED.value,
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "created_by": str(created_by),
                "created_by_name": created_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"New event created: {event_title}"
            }
            
            # Broadcast based on event visibility
            from app.api.v1.models.event_model import Event, EventParticipant, EventVisibility
            
            event = db.query(Event).filter(Event.id == int(event_id)).first()
            if event:
                if event.visibility == EventVisibility.ALL:
                    # Broadcast to all tenant users
                    await manager.broadcast_to_tenant(
                        tenant_id=int(tenant_id),
                        message=message,
                        exclude_connection_id=connection_id
                    )
                elif event.visibility == EventVisibility.DEPARTMENT:
                    # Broadcast to department users (handled by role-based rooms)
                    # For now, broadcast to tenant and let frontend filter
                    await manager.broadcast_to_tenant(
                        tenant_id=int(tenant_id),
                        message=message,
                        exclude_connection_id=connection_id
                    )
                elif event.visibility == EventVisibility.SELECTED_USERS:
                    # Send to selected users only
                    participants = db.query(EventParticipant).filter(
                        EventParticipant.event_id == int(event_id)
                    ).all()
                    
                    for participant in participants:
                        await manager.send_to_user(
                            tenant_id=int(tenant_id),
                            user_id=participant.user_id,
                            message=message
                        )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Event created event broadcasted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error handling event_created event: {e}")
    
    @staticmethod
    async def handle_event_updated(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle EVENT_UPDATED event
        Broadcasts to: All users based on event visibility
        """
        try:
            tenant_id = event_data.get('tenant_id')
            event_id = event_data.get('event_id')
            event_title = event_data.get('event_title')
            event_type = event_data.get('event_type')
            updated_by = event_data.get('updated_by')
            updated_by_name = event_data.get('updated_by_name', 'Admin')
            
            message = {
                "event": EventType.EVENT_UPDATED.value,
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "updated_by": str(updated_by),
                "updated_by_name": updated_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Event updated: {event_title}"
            }
            
            # Broadcast based on event visibility (similar to created)
            from app.api.v1.models.event_model import Event, EventParticipant, EventVisibility
            
            event = db.query(Event).filter(Event.id == int(event_id)).first()
            if event:
                if event.visibility == EventVisibility.ALL:
                    await manager.broadcast_to_tenant(
                        tenant_id=int(tenant_id),
                        message=message,
                        exclude_connection_id=connection_id
                    )
                elif event.visibility == EventVisibility.SELECTED_USERS:
                    participants = db.query(EventParticipant).filter(
                        EventParticipant.event_id == int(event_id)
                    ).all()
                    
                    for participant in participants:
                        await manager.send_to_user(
                            tenant_id=int(tenant_id),
                            user_id=participant.user_id,
                            message=message
                        )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Event updated event broadcasted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error handling event_updated event: {e}")
    
    @staticmethod
    async def handle_event_cancelled(
        event_data: Dict[str, Any],
        db: Session,
        connection_id: Optional[str] = None
    ):
        """
        Handle EVENT_CANCELLED event
        Broadcasts to: All users based on event visibility
        """
        try:
            tenant_id = event_data.get('tenant_id')
            event_id = event_data.get('event_id')
            event_title = event_data.get('event_title')
            event_type = event_data.get('event_type')
            cancelled_by = event_data.get('cancelled_by')
            cancelled_by_name = event_data.get('cancelled_by_name', 'Admin')
            
            message = {
                "event": EventType.EVENT_CANCELLED.value,
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "event_title": event_title,
                "event_type": event_type,
                "cancelled_by": str(cancelled_by),
                "cancelled_by_name": cancelled_by_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Event cancelled: {event_title}"
            }
            
            # Broadcast to tenant (event might be deleted, so broadcast widely)
            await manager.broadcast_to_tenant(
                tenant_id=int(tenant_id),
                message=message,
                exclude_connection_id=connection_id
            )
            
            # Publish to Redis
            if redis_pubsub.is_connected:
                channel = redis_pubsub.get_tenant_channel(int(tenant_id))
                await redis_pubsub.publish(channel, message)
            
            logger.info(f"Event cancelled event broadcasted: {event_title}")
            
        except Exception as e:
            logger.error(f"Error handling event_cancelled event: {e}")


# Event handler instance
event_handler = EventHandler()

