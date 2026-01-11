"""
File upload utility functions for handling employee attachments
Supports both S3 and local file storage
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
import logging
from io import BytesIO

from app.core.config import settings
from app.api.v1.utils.s3_service import get_s3_service

logger = logging.getLogger(__name__)


def get_upload_directory() -> Path:
    """Get the base upload directory path"""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_employee_upload_directory(company_id: int, employee_id: int) -> Path:
    """Get the upload directory for a specific employee"""
    base_dir = get_upload_directory()
    employee_dir = base_dir / f"company_{company_id}" / f"employee_{employee_id}"
    employee_dir.mkdir(parents=True, exist_ok=True)
    return employee_dir


def validate_file_type(file: UploadFile, is_image: bool = False, allow_both: bool = False) -> None:
    """
    Validate file type based on allowed MIME types
    
    Args:
        file: The uploaded file
        is_image: Whether this should be an image file
        allow_both: If True, allows both image and document types
        
    Raises:
        HTTPException: If file type is not allowed
    """
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content type is missing"
        )
    
    # Determine which types to check
    if allow_both:
        # Allow both images and documents
        allowed_types = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOCUMENT_TYPES
    elif is_image:
        allowed_types = settings.ALLOWED_IMAGE_TYPES
    else:
        allowed_types = settings.ALLOWED_DOCUMENT_TYPES
    
    if file.content_type not in allowed_types:
        type_category = "images or documents" if allow_both else ("images" if is_image else "documents")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} is not allowed for {type_category}. Allowed types: {', '.join(allowed_types)}"
        )


def validate_file_size(file_size: int) -> None:
    """
    Validate file size
    
    Args:
        file_size: File size in bytes
        
    Raises:
        HTTPException: If file size exceeds maximum
    """
    if file_size > settings.MAX_FILE_SIZE:
        max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {max_size_mb:.1f}MB"
        )


def save_uploaded_file(
    file: UploadFile,
    company_id: int,
    employee_id: int,
    attachment_type: str,
    is_image: bool = False,
    allow_both: bool = False
) -> Tuple[str, str, int]:
    """
    Save an uploaded file to S3 or local storage
    
    Args:
        file: The uploaded file
        company_id: Company ID
        employee_id: Employee ID
        attachment_type: Type of attachment (for subdirectory organization)
        is_image: Whether this is an image file
        allow_both: If True, allows both image and document types
        
    Returns:
        Tuple of (file_path/s3_key, file_name, file_size)
        
    Raises:
        HTTPException: If file validation fails or save operation fails
    """
    # Validate file type
    validate_file_type(file, is_image, allow_both=allow_both)
    
    # Read file content to get size
    file_content = file.file.read()
    file_size = len(file_content)
    
    # Validate file size
    validate_file_size(file_size)
    
    # Reset file pointer
    file.file.seek(0)
    
    # Get MIME type
    mime_type = getattr(file, 'content_type', None) or "application/octet-stream"
    original_filename = file.filename or f"file_{uuid.uuid4()}"
    
    # Generate unique filename
    file_extension = Path(original_filename).suffix if original_filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Try S3 first if enabled
    s3_service = get_s3_service()
    if s3_service:
        try:
            # Generate S3 key (path in bucket)
            s3_key = f"company_{company_id}/employee_{employee_id}/{attachment_type}/{unique_filename}"
            
            # Create file-like object from bytes
            file_obj = BytesIO(file_content)
            
            # Upload to S3
            s3_service.upload_file(
                file_obj=file_obj,
                s3_key=s3_key,
                content_type=mime_type,
                metadata={
                    'original_filename': original_filename,
                    'employee_id': str(employee_id),
                    'company_id': str(company_id),
                    'attachment_type': attachment_type
                }
            )
            
            # Return S3 key as file_path
            return s3_key, original_filename, file_size
            
        except Exception as e:
            logger.error(f"Error uploading to S3, falling back to local storage: {str(e)}")
            # Fall through to local storage
    
    # Fallback to local storage
    upload_dir = get_employee_upload_directory(company_id, employee_id)
    
    # Create subdirectory for attachment type if needed
    type_dir = upload_dir / attachment_type
    type_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = type_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Return relative path (from upload directory)
        relative_path = str(file_path.relative_to(get_upload_directory()))
        
        return relative_path, original_filename, file_size
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


def delete_file(file_path: str) -> None:
    """
    Delete a file from S3 or local storage
    
    Args:
        file_path: S3 key or relative path to the file
    """
    # Try S3 first if enabled
    s3_service = get_s3_service()
    if s3_service:
        try:
            # Check if it looks like an S3 key (contains company_/employee_ pattern)
            if file_path.startswith("company_") or "/" in file_path:
                if s3_service.delete_file(file_path):
                    return
        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            # Fall through to local storage
    
    # Fallback to local storage
    try:
        upload_dir = get_upload_directory()
        full_path = upload_dir / file_path
        
        if full_path.exists():
            full_path.unlink()
            
            # Try to remove empty parent directories
            parent = full_path.parent
            while parent != upload_dir and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
            
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        # Don't raise exception - file deletion failure shouldn't break the flow


def get_file_path(file_path: str) -> Optional[Path]:
    """
    Get the full path to a file (for local storage only)
    For S3 files, use get_s3_download_url() instead
    
    Args:
        file_path: Relative path to the file (from upload directory)
        
    Returns:
        Full Path object if file exists, None otherwise
    """
    # If using S3, return None (files are in S3, not local)
    s3_service = get_s3_service()
    if s3_service and file_path.startswith("company_"):
        return None
    
    upload_dir = get_upload_directory()
    full_path = upload_dir / file_path
    
    if full_path.exists():
        return full_path
    return None


def get_s3_download_url(file_path: str, expiration: int = 3600) -> Optional[str]:
    """
    Get a presigned URL for downloading a file from S3
    
    Args:
        file_path: S3 key (path in bucket)
        expiration: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Presigned URL string if S3 is enabled, None otherwise
    """
    s3_service = get_s3_service()
    if s3_service:
        try:
            return s3_service.generate_presigned_url(
                file_path, 
                expiration=expiration,
                response_content_disposition='attachment'
            )
        except Exception as e:
            logger.error(f"Error generating S3 download URL: {str(e)}")
            return None
    return None


def get_s3_view_url(file_path: str, mime_type: Optional[str] = None, expiration: int = 3600) -> Optional[str]:
    """
    Get a presigned URL for viewing a file inline from S3 (e.g., for img tags)
    
    Args:
        file_path: S3 key (path in bucket)
        mime_type: MIME type of the file (for proper content-type header)
        expiration: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Presigned URL string if S3 is enabled, None otherwise
    """
    s3_service = get_s3_service()
    if s3_service:
        try:
            return s3_service.generate_view_url(
                file_path,
                expiration=expiration,
                content_type=mime_type
            )
        except Exception as e:
            logger.error(f"Error generating S3 view URL: {str(e)}")
            return None
    return None


def get_file_content(file_path: str) -> Optional[bytes]:
    """
    Get file content from S3 or local storage
    
    Args:
        file_path: S3 key or relative path to the file
        
    Returns:
        File content as bytes, or None if file doesn't exist
    """
    # Try S3 first if enabled
    s3_service = get_s3_service()
    if s3_service:
        try:
            # Check if it looks like an S3 key
            if file_path.startswith("company_") or "/" in file_path:
                content = s3_service.download_file(file_path)
                if content:
                    return content
        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            # Fall through to local storage
    
    # Fallback to local storage
    try:
        upload_dir = get_upload_directory()
        full_path = upload_dir / file_path
        
        if full_path.exists():
            with open(full_path, "rb") as f:
                return f.read()
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
    
    return None
