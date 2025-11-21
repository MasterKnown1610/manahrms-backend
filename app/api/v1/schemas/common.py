from pydantic import BaseModel
from typing import Generic, List, TypeVar, Optional, Any


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    limit: int
    items: List[T]


class ErrorResponse(BaseModel):
    """Standard error response format for all API errors"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None
    
    model_config = {"json_schema_extra": {
        "example": {
            "success": False,
            "message": "Error message describing what went wrong",
            "error_code": "ERROR_CODE",
            "details": {"field": "Additional error details if needed"}
        }
    }}


