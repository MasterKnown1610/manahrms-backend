"""
Helper utilities for WebSocket event emission from synchronous code
"""
import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def emit_websocket_event_async(
    coro,
    db: Optional[Session] = None
):
    """
    Helper to emit WebSocket events from synchronous code
    
    Usage:
        emit_websocket_event_async(
            websocket_service.emit_attendance_marked(
                db=db,
                tenant_id=company_id,
                employee_id=employee_id,
                employee_name=employee.full_name,
                action="LOGIN"
            )
        )
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop is already running, create task
            asyncio.create_task(coro)
        else:
            # No event loop running, run until complete
            loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create new one
        try:
            asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error emitting WebSocket event: {e}")
    except Exception as e:
        logger.error(f"Error emitting WebSocket event: {e}")

