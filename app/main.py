from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db, engine
from app.core.config import settings
from app.api.router import api_router
from app.db.base import Base

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="HRMS SaaS Backend with Authentication APIs"
)


@app.on_event("startup")
async def startup():
    """Test database connection and create tables on startup"""
    print(f"🚀 Starting {settings.PROJECT_NAME}...")
    print(f"📊 Database: {settings.DATABASE_NAME}")
    
    try:
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connected successfully!")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to HRMS Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "database": settings.DATABASE_NAME,
        "status": "running"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database verification"""
    try:
        # Test database query
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


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
