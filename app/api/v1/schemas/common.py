from pydantic import BaseModel, Field
from typing import Generic, List, TypeVar, Optional, Any, Dict
from enum import Enum


T = TypeVar("T")


class SortOrder(str, Enum):
    """Sort order enumeration"""
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    """Filter operator enumeration"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class FilterCondition(BaseModel):
    """Single filter condition"""
    field: str = Field(..., description="Field name to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")


class SortCondition(BaseModel):
    """Sort condition"""
    field: str = Field(..., description="Field name to sort by")
    order: SortOrder = Field(SortOrder.ASC, description="Sort order (asc/desc)")


class PaginationRequest(BaseModel):
    """Pagination request payload"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")
    sort: Optional[List[SortCondition]] = Field(None, description="Sort conditions")
    filter: Optional[List[FilterCondition]] = Field(None, description="Filter conditions")
    
    model_config = {"json_schema_extra": {
        "example": {
            "page": 1,
            "page_size": 20,
            "sort": [
                {"field": "created_at", "order": "desc"}
            ],
            "filter": [
                {"field": "is_active", "operator": "eq", "value": True}
            ]
        }
    }}


class PaginationInfo(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format"""
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")
    
    model_config = {"json_schema_extra": {
        "example": {
            "data": [],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        }
    }}


# Legacy pagination response (for backward compatibility)
class LegacyPaginatedResponse(BaseModel, Generic[T]):
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


