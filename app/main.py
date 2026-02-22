from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

from app.db.session import get_database_session, engine
from app.core.config import settings
from app.api.router import api_router
from app.db.init_db import initialize_database_on_startup
from app.api.v1.utils.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

# Configure logging
def setup_logging():
    """Configure comprehensive logging for the application"""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - INFO level and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - DEBUG level and above (all logs)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler - ERROR level and above
    error_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)
    
    # Set levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    root_logger.info("Logging configured successfully")

# Setup logging before creating logger
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="HRMS SaaS Backend with Authentication APIs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    import time
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"IP: {request.client.host if request.client else 'unknown'} - "
        f"Query params: {dict(request.query_params)}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - "
            f"Error: {type(e).__name__}: {str(e)} - "
            f"Time: {process_time:.3f}s",
            exc_info=True
        )
        raise

# Register custom exception handlers for consistent error format
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.on_event("startup")
async def initialize_application_on_startup():
    try:
        with engine.connect() as conn:
            pass
        
        initialize_database_on_startup()
        
        # Initialize Redis for WebSocket Pub/Sub
        try:
            from app.api.v1.websocket.redis_pubsub import redis_pubsub
            from app.api.v1.routes.websocket import handle_redis_message
            
            redis_url = None
            if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
                redis_url = settings.REDIS_URL
            elif hasattr(settings, 'REDIS_PASSWORD') and settings.REDIS_PASSWORD:
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            else:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
            await redis_pubsub.connect(redis_url)
            
            # Subscribe to tenant channels (this will be done dynamically per tenant)
            # Start Redis listener in background
            import asyncio
            asyncio.create_task(redis_pubsub.listen())
            
            logger.info("Redis Pub/Sub initialized for WebSocket")
        except Exception as e:
            logger.warning(f"Redis connection failed (WebSocket Pub/Sub will be disabled): {e}")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")


@app.get("/")
def get_root_endpoint():
    return {
        "message": "Welcome to HRMS Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "database": settings.DATABASE_NAME,
        "status": "running"
    }


@app.get("/health")
def check_application_health(db: Session = Depends(get_database_session)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "database_name": settings.DATABASE_NAME
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include WebSocket router (no prefix for /ws endpoint)
from app.api.v1.routes import websocket
app.include_router(websocket.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
