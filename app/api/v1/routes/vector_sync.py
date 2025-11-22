"""
Vector Sync routes for managing embeddings
Allows syncing company data to vector store for RAG
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.services.vector_sync_service import VectorSyncService


router = APIRouter(prefix="/vector-sync", tags=["Vector Sync"])


class SyncResponse(BaseModel):
    """Response schema for vector sync"""
    success: bool
    message: str
    stats: dict = {}


@router.post("/sync-company", response_model=SyncResponse, status_code=status.HTTP_200_OK)
async def sync_company_vectors(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Sync all company data to vector store for semantic search.
    This should be called after bulk data updates or periodically.
    
    Note: This operation may take some time depending on the amount of data.
    """
    try:
        sync_service = VectorSyncService()
        stats = sync_service.sync_company_data(db, current_user.company_id)
        
        return SyncResponse(
            success=True,
            message="Vector sync completed successfully",
            stats=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing vectors: {str(e)}"
        )

