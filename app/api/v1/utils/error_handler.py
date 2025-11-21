"""
Common error handling utilities for consistent error responses across the application.
"""
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional, Any

from app.api.v1.schemas.common import ErrorResponse


def create_error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Optional error code for programmatic handling
        details: Optional additional error details
    
    Returns:
        JSONResponse with standardized error format
    """
    error_response = ErrorResponse(
        success=False,
        message=message,
        error_code=error_code,
        details=details
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True)
    )


def raise_http_exception(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Any] = None
) -> None:
    """
    Raise an HTTPException with standardized error format.
    This function should be used instead of directly raising HTTPException.
    
    Args:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Optional error code for programmatic handling
        details: Optional additional error details
    
    Raises:
        HTTPException with standardized detail format
    """
    error_detail = {
        "success": False,
        "message": message,
    }
    
    if error_code:
        error_detail["error_code"] = error_code
    
    if details:
        error_detail["details"] = details
    
    raise HTTPException(
        status_code=status_code,
        detail=error_detail
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Custom handler for HTTPException to return standardized error format.
    """
    # Check if detail is already in our format
    if isinstance(exc.detail, dict) and "message" in exc.detail:
        error_detail = exc.detail
    else:
        # Convert string detail to our format
        error_detail = {
            "success": False,
            "message": str(exc.detail) if exc.detail else "An error occurred",
        }
    
    error_response = ErrorResponse(**error_detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
        headers=getattr(exc, "headers", None)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Custom handler for validation errors to return standardized error format.
    """
    errors = exc.errors()
    error_messages = []
    error_details = {}
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
        error_details[field] = message
    
    error_response = ErrorResponse(
        success=False,
        message="Validation error: " + "; ".join(error_messages),
        error_code="VALIDATION_ERROR",
        details=error_details
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Custom handler for unhandled exceptions to return standardized error format.
    """
    error_response = ErrorResponse(
        success=False,
        message="An unexpected error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR",
        details={"type": type(exc).__name__} if hasattr(exc, "__class__") else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True)
    )

