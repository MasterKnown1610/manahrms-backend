"""
Redis Pub/Sub Integration for Horizontal Scaling
Allows multiple WebSocket server instances to communicate via Redis
"""
import json
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisPubSub:
    """
    Redis Pub/Sub manager for cross-instance WebSocket communication
    """
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.subscribed_channels: set = set()
        self.message_handlers: Dict[str, Callable] = {}
        self.is_connected = False
    
    async def connect(self, redis_url: Optional[str] = None):
        """Connect to Redis"""
        try:
            if redis_url:
                self.redis_client = await Redis.from_url(redis_url, decode_responses=True)
            elif hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
                self.redis_client = await Redis.from_url(settings.REDIS_URL, decode_responses=True)
            else:
                # Default Redis connection
                self.redis_client = await Redis.from_url(
                    "redis://localhost:6379",
                    decode_responses=True
                )
            
            self.pubsub = self.redis_client.pubsub()
            self.is_connected = True
            logger.info("Connected to Redis for Pub/Sub")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        self.is_connected = False
        logger.info("Disconnected from Redis")
    
    async def publish(self, channel: str, message: dict):
        """Publish message to Redis channel"""
        if not self.is_connected or not self.redis_client:
            logger.warning("Redis not connected, cannot publish")
            return
        
        try:
            message_json = json.dumps(message)
            await self.redis_client.publish(channel, message_json)
            logger.debug(f"Published to channel {channel}: {message.get('event', 'unknown')}")
        except Exception as e:
            logger.error(f"Error publishing to Redis channel {channel}: {e}")
    
    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to Redis channel with message handler"""
        if not self.is_connected or not self.pubsub:
            logger.warning("Redis not connected, cannot subscribe")
            return
        
        try:
            await self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            self.message_handlers[channel] = handler
            logger.info(f"Subscribed to Redis channel: {channel}")
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from Redis channel"""
        if not self.pubsub:
            return
        
        try:
            await self.pubsub.unsubscribe(channel)
            self.subscribed_channels.discard(channel)
            if channel in self.message_handlers:
                del self.message_handlers[channel]
            logger.info(f"Unsubscribed from Redis channel: {channel}")
        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel}: {e}")
    
    async def listen(self):
        """Listen for messages from subscribed channels"""
        if not self.is_connected or not self.pubsub:
            return
        
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    
                    # Parse JSON message
                    try:
                        message_data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in Redis message from {channel}")
                        continue
                    
                    # Call handler if exists
                    if channel in self.message_handlers:
                        handler = self.message_handlers[channel]
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message_data)
                            else:
                                handler(message_data)
                        except Exception as e:
                            logger.error(f"Error in message handler for {channel}: {e}")
        except Exception as e:
            logger.error(f"Error listening to Redis messages: {e}")
    
    def get_tenant_channel(self, tenant_id: int) -> str:
        """Get Redis channel name for tenant"""
        return f"tenant:{tenant_id}"
    
    def get_role_channel(self, tenant_id: int, role: str) -> str:
        """Get Redis channel name for role"""
        return f"tenant:{tenant_id}:role:{role}"
    
    def get_user_channel(self, tenant_id: int, user_id: int) -> str:
        """Get Redis channel name for user"""
        return f"tenant:{tenant_id}:user:{user_id}"


# Global Redis Pub/Sub instance
redis_pubsub = RedisPubSub()

