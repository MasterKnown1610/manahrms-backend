from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_database_session, engine
from app.core.config import settings
from app.api.router import api_router
from app.db.init_db import initialize_database_on_startup
from app.api.v1.utils.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

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

# Register custom exception handlers for consistent error format
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.on_event("startup")
async def initialize_application_on_startup():
    print(f"Starting {settings.PROJECT_NAME}...")
    print(f"Database: {settings.DATABASE_NAME}")
    
    try:
        with engine.connect() as conn:
            print("Database connected successfully!")
        
        if initialize_database_on_startup():
            print("Database initialization complete!")
        else:
            print("Database initialization had issues, but continuing...")
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Server will continue, but database operations may fail.")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
