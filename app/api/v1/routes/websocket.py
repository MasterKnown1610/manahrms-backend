"""
WebSocket Routes for Real-time Communication
"""
import json
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.websocket.auth import authenticate_websocket
from app.api.v1.websocket.connection_manager import manager
from app.api.v1.websocket.redis_pubsub import redis_pubsub
from app.api.v1.websocket.event_handlers import event_handler
from app.api.v1.schemas.websocket_schema import (
    SubscriptionPlan,
    EventType,
    WebSocketError
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_subscription_plan(user) -> SubscriptionPlan:
    """
    Get subscription plan for user/company
    TODO: Implement actual subscription plan lookup from database
    For now, defaulting to PRO plan
    """
    # This should query the company's subscription plan
    # For now, returning PRO as default
    return SubscriptionPlan.PRO


async def handle_redis_message(message_data: dict):
    """
    Handle messages received from Redis Pub/Sub
    Broadcasts to local WebSocket connections
    """
    try:
        event_type = message_data.get('event')
        tenant_id = int(message_data.get('tenant_id', 0))
        
        if not tenant_id:
            return
        
        # Broadcast to appropriate rooms based on event type
        if event_type == EventType.ATTENDANCE_MARKED.value:
            # Broadcast to Admin, HR, Manager roles
            for role in ['ADMIN', 'HR', 'MANAGER']:
                await manager.broadcast_to_role(tenant_id, role, message_data)
        
        elif event_type == EventType.TASK_STATUS_UPDATED.value:
            # Broadcast to Admin
            await manager.broadcast_to_role(tenant_id, 'ADMIN', message_data)
            # Also send to specific user if mentioned
            assigned_to = message_data.get('assigned_to_employee_id')
            if assigned_to:
                await manager.send_to_user(tenant_id, int(assigned_to), message_data)
        
        elif event_type == EventType.TASK_ASSIGNED.value:
            # Send to assigned user
            assigned_to = message_data.get('assigned_to')
            if assigned_to:
                await manager.send_to_user(tenant_id, int(assigned_to), message_data)
        
        elif event_type == EventType.EMPLOYEE_ACTIVITY.value:
            # Broadcast to Admin
            await manager.broadcast_to_role(tenant_id, 'ADMIN', message_data)
        
        elif event_type == EventType.DASHBOARD_UPDATE.value:
            # Broadcast to Admin and HR
            for role in ['ADMIN', 'HR']:
                await manager.broadcast_to_role(tenant_id, role, message_data)
        
        elif event_type == EventType.MEETING_CREATED.value:
            # Broadcast to all participants (handled in event handler)
            # Get db session for meeting handlers
            db_session = next(get_database_session())
            try:
                await event_handler.handle_meeting_created(message_data, db_session)
            finally:
                db_session.close()
        
        elif event_type == EventType.MEETING_UPDATED.value:
            # Broadcast to all participants (handled in event handler)
            db_session = next(get_database_session())
            try:
                await event_handler.handle_meeting_updated(message_data, db_session)
            finally:
                db_session.close()
        
        elif event_type == EventType.MEETING_CANCELLED.value:
            # Broadcast to all participants (handled in event handler)
            db_session = next(get_database_session())
            try:
                await event_handler.handle_meeting_cancelled(message_data, db_session)
            finally:
                db_session.close()
        
        elif event_type == EventType.EVENT_CREATED.value:
            # Broadcast based on visibility (handled in event handler)
            db_session = next(get_database_session())
            try:
                await event_handler.handle_event_created(message_data, db_session)
            finally:
                db_session.close()
        
        elif event_type == EventType.EVENT_UPDATED.value:
            # Broadcast based on visibility (handled in event handler)
            db_session = next(get_database_session())
            try:
                await event_handler.handle_event_updated(message_data, db_session)
            finally:
                db_session.close()
        
        elif event_type == EventType.EVENT_CANCELLED.value:
            # Broadcast to tenant (handled in event handler)
            db_session = next(get_database_session())
            try:
                await event_handler.handle_event_cancelled(message_data, db_session)
            finally:
                db_session.close()
        
    except Exception as e:
        logger.error(f"Error handling Redis message: {e}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time communication
    
    Connection URL: wss://api.manahrms.com/ws?token=JWT_TOKEN
    
    On connection:
    - Validates JWT token
    - Joins tenant, role, and user-specific rooms
    - Sends connection confirmation
    
    Message format:
    {
        "event": "PING",
        "data": {}
    }
    """
    connection_id = None
    
    try:
        # Authenticate user
        user = await authenticate_websocket(websocket, token)
        if not user:
            return
        
        # Get subscription plan
        subscription_plan = get_subscription_plan(user)
        
        # Connect and join rooms
        connection_id = await manager.connect(websocket, user, subscription_plan)
        
        # Send connection confirmation
        await websocket.send_json({
            "event": EventType.CONNECTED.value,
            "tenant_id": str(user.company_id),
            "user_id": str(user.id),
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "subscription_plan": subscription_plan.value,
            "timestamp": asyncio.get_event_loop().time(),
            "message": "WebSocket connection established"
        })
        
        logger.info(f"WebSocket connected successfully: {connection_id}")
        
        # Note: Redis subscription is handled globally, not per connection
        # The listener is started once on application startup
        
        # Heartbeat/ping-pong handling
        last_ping = asyncio.get_event_loop().time()
        PING_INTERVAL = 30  # seconds
        TIMEOUT = 60  # seconds
        
        # Main message loop
        while True:
            try:
                # Check for timeout
                current_time = asyncio.get_event_loop().time()
                if current_time - last_ping > TIMEOUT:
                    # Send ping
                    await websocket.send_json({
                        "event": EventType.PING.value,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    last_ping = current_time
                
                # Wait for message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=PING_INTERVAL
                )
                
                # Parse message
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "event": EventType.ERROR.value,
                        "error_code": "INVALID_JSON",
                        "message": "Invalid JSON format"
                    })
                    continue
                
                # Check rate limit
                if not manager.check_rate_limit(connection_id, max_messages=100, window_seconds=60):
                    await websocket.send_json({
                        "event": EventType.ERROR.value,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many messages. Please slow down."
                    })
                    continue
                
                # Handle different event types
                event = message.get('event')
                
                if event == EventType.PONG.value:
                    # Respond to ping
                    await websocket.send_json({
                        "event": EventType.PONG.value,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    last_ping = asyncio.get_event_loop().time()
                
                elif event == EventType.PING.value:
                    # Client ping, respond with pong
                    await websocket.send_json({
                        "event": EventType.PONG.value,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    last_ping = asyncio.get_event_loop().time()
                
                else:
                    # Unknown event
                    logger.warning(f"Unknown event type received: {event}")
                    await websocket.send_json({
                        "event": EventType.ERROR.value,
                        "error_code": "UNKNOWN_EVENT",
                        "message": f"Unknown event type: {event}"
                    })
                
            except asyncio.TimeoutError:
                # Timeout - send ping
                await websocket.send_json({
                    "event": EventType.PING.value,
                    "timestamp": asyncio.get_event_loop().time()
                })
                last_ping = asyncio.get_event_loop().time()
                continue
            
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "event": EventType.ERROR.value,
                "error_code": "INTERNAL_ERROR",
                "message": "An internal error occurred"
            })
        except:
            pass
    
    finally:
        # Clean up connection
        if connection_id:
            manager.disconnect(connection_id)
            logger.info(f"WebSocket connection cleaned up: {connection_id}")

