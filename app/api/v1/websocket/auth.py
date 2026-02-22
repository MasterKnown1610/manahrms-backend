"""
WebSocket Authentication Utilities
"""
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.core.security import decode_and_verify_jwt_token
from app.api.v1.models.user_model import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = None
) -> Optional[User]:
    """
    Authenticate WebSocket connection using JWT token
    
    Token can be provided via:
    1. Query parameter: ?token=JWT_TOKEN
    2. Subprotocol header
    """
    # Try to get token from query parameter
    if not token:
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return None
    
    # Decode and verify JWT
    payload = decode_and_verify_jwt_token(token)
    if payload is None:
        await websocket.close(code=1008, reason="Invalid authentication token")
        return None
    
    username: str = payload.get("sub")
    if username is None:
        await websocket.close(code=1008, reason="Invalid token payload")
        return None
    
    # Get database session
    db = next(get_database_session())
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if user is None:
            await websocket.close(code=1008, reason="User not found")
            return None
        
        if not user.is_active:
            await websocket.close(code=1008, reason="User account is inactive")
            return None
        
        if not user.company.is_active:
            await websocket.close(code=1008, reason="Company account is inactive")
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Error authenticating WebSocket: {e}")
        await websocket.close(code=1011, reason="Internal server error")
        return None
    finally:
        db.close()

