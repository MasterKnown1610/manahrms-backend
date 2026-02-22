"""
WebSocket Connection Manager for Multi-tenant Real-time Communication
Handles connection lifecycle, room management, and message broadcasting
"""
import json
import asyncio
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.schemas.websocket_schema import (
    WebSocketMessage,
    WebSocketConnectionInfo,
    SubscriptionPlan,
    EventType
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with tenant-based room isolation
    """
    
    def __init__(self):
        # Active connections: {websocket_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection metadata: {websocket_id: ConnectionInfo}
        self.connection_info: Dict[str, WebSocketConnectionInfo] = {}
        
        # Room management: {room_name: Set[websocket_id]}
        self.rooms: Dict[str, Set[str]] = {}
        
        # User to connection mapping: {user_id: Set[websocket_id]}
        self.user_connections: Dict[int, Set[str]] = {}
        
        # Rate limiting: {websocket_id: (count, last_reset)}
        self.rate_limits: Dict[str, tuple] = {}
        
    def _generate_connection_id(self, user_id: int, tenant_id: int) -> str:
        """Generate unique connection ID"""
        return f"{tenant_id}:{user_id}:{datetime.utcnow().timestamp()}"
    
    def _get_tenant_room(self, tenant_id: int) -> str:
        """Get tenant room name"""
        return f"tenant:{tenant_id}"
    
    def _get_role_room(self, tenant_id: int, role: str) -> str:
        """Get role-based room name"""
        return f"tenant:{tenant_id}:role:{role}"
    
    def _get_user_room(self, tenant_id: int, user_id: int) -> str:
        """Get user-specific room name"""
        return f"tenant:{tenant_id}:user:{user_id}"
    
    async def connect(
        self,
        websocket: WebSocket,
        user: User,
        subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    ) -> str:
        """
        Connect a WebSocket client and join appropriate rooms
        
        Returns connection_id
        """
        await websocket.accept()
        
        connection_id = self._generate_connection_id(user.id, user.company_id)
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Determine subscription plan (can be from user model or default)
        # For now, using parameter, but should be fetched from user/company model
        
        # Create connection info
        connection_info = WebSocketConnectionInfo(
            user_id=user.id,
            tenant_id=user.company_id,
            role=user.role.value if isinstance(user.role, UserRole) else user.role,
            subscription_plan=subscription_plan
        )
        
        # Join rooms
        tenant_room = self._get_tenant_room(user.company_id)
        role_room = self._get_role_room(user.company_id, connection_info.role)
        user_room = self._get_user_room(user.company_id, user.id)
        
        self._join_room(connection_id, tenant_room)
        self._join_room(connection_id, role_room)
        self._join_room(connection_id, user_room)
        
        connection_info.rooms = [tenant_room, role_room, user_room]
        self.connection_info[connection_id] = connection_info
        
        # Track user connections
        if user.id not in self.user_connections:
            self.user_connections[user.id] = set()
        self.user_connections[user.id].add(connection_id)
        
        # Initialize rate limit
        self.rate_limits[connection_id] = (0, datetime.utcnow())
        
        logger.info(
            f"WebSocket connected: {connection_id} | "
            f"User: {user.id} | Tenant: {user.company_id} | Role: {connection_info.role}"
        )
        
        # Send connection confirmation
        await self.send_personal_message(
            connection_id,
            {
                "event": EventType.CONNECTED.value,
                "tenant_id": str(user.company_id),
                "message": "Connected to ManaHRMS WebSocket",
                "connection_id": connection_id,
                "subscription_plan": subscription_plan.value,
                "rooms": connection_info.rooms,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return connection_id
    
    def _join_room(self, connection_id: str, room_name: str):
        """Add connection to a room"""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(connection_id)
    
    def _leave_room(self, connection_id: str, room_name: str):
        """Remove connection from a room"""
        if room_name in self.rooms:
            self.rooms[room_name].discard(connection_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
    
    def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.connection_info.get(connection_id)
        if connection_info:
            # Leave all rooms
            for room in connection_info.rooms:
                self._leave_room(connection_id, room)
            
            # Remove from user connections
            user_id = connection_info.user_id
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        # Clean up
        del self.active_connections[connection_id]
        if connection_id in self.connection_info:
            del self.connection_info[connection_id]
        if connection_id in self.rate_limits:
            del self.rate_limits[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, connection_id: str, message: dict):
        """Send message to a specific connection"""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self.disconnect(connection_id)
    
    async def send_to_user(self, tenant_id: int, user_id: int, message: dict):
        """Send message to all connections of a specific user"""
        user_room = self._get_user_room(tenant_id, user_id)
        await self.broadcast_to_room(user_room, message)
    
    async def broadcast_to_room(self, room_name: str, message: dict):
        """Broadcast message to all connections in a room"""
        if room_name not in self.rooms:
            return
        
        connection_ids = list(self.rooms[room_name])
        disconnected = []
        
        for connection_id in connection_ids:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    disconnected.append(connection_id)
            else:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_role(
        self,
        tenant_id: int,
        role: str,
        message: dict,
        exclude_connection_id: Optional[str] = None
    ):
        """Broadcast message to all connections with a specific role in a tenant"""
        role_room = self._get_role_room(tenant_id, role)
        if role_room not in self.rooms:
            return
        
        connection_ids = list(self.rooms[role_room])
        if exclude_connection_id:
            connection_ids = [cid for cid in connection_ids if cid != exclude_connection_id]
        
        disconnected = []
        for connection_id in connection_ids:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to role {role}: {e}")
                    disconnected.append(connection_id)
            else:
                disconnected.append(connection_id)
        
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_tenant(
        self,
        tenant_id: int,
        message: dict,
        exclude_connection_id: Optional[str] = None
    ):
        """Broadcast message to all connections in a tenant"""
        tenant_room = self._get_tenant_room(tenant_id)
        await self.broadcast_to_room(tenant_room, message)
    
    def check_rate_limit(self, connection_id: str, max_messages: int = 100, window_seconds: int = 60) -> bool:
        """Check if connection is within rate limit"""
        if connection_id not in self.rate_limits:
            self.rate_limits[connection_id] = (0, datetime.utcnow())
            return True
        
        count, last_reset = self.rate_limits[connection_id]
        now = datetime.utcnow()
        
        # Reset if window expired
        if (now - last_reset).total_seconds() > window_seconds:
            self.rate_limits[connection_id] = (1, now)
            return True
        
        # Check limit
        if count >= max_messages:
            return False
        
        # Increment count
        self.rate_limits[connection_id] = (count + 1, last_reset)
        return True
    
    def get_connection_info(self, connection_id: str) -> Optional[WebSocketConnectionInfo]:
        """Get connection information"""
        return self.connection_info.get(connection_id)
    
    def get_active_connections_count(self, tenant_id: Optional[int] = None) -> int:
        """Get count of active connections"""
        if tenant_id is None:
            return len(self.active_connections)
        
        count = 0
        for conn_info in self.connection_info.values():
            if conn_info.tenant_id == tenant_id:
                count += 1
        return count


# Global connection manager instance
manager = ConnectionManager()

