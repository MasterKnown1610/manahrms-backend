from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_database_session
from app.api.v1.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeWithCredentials,
    EmployeeDropdownResponse
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.schemas.common import PaginatedResponse, PaginationRequest
from app.api.v1.schemas.employee_attachment_schema import (
    EmployeeAttachmentResponse,
    EmployeeAttachmentListResponse
)
from app.api.v1.services.employee_service import EmployeeService
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.utils.pagination import paginate_query, create_paginated_response
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.employee_attachment_model import AttachmentType
from app.api.v1.utils.file_upload import get_file_path, get_s3_download_url, get_s3_view_url, get_file_content
from app.core.config import settings


router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("/create", response_model=EmployeeWithCredentials, status_code=status.HTTP_201_CREATED)
async def create_new_employee(
    employee_data: EmployeeCreate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    employee, user, temp_password = EmployeeService.create_employee_with_credentials(
        db, 
        employee_data, 
        current_user.company_id
    )
    
    return EmployeeWithCredentials(
        employee=EmployeeResponse.model_validate(employee),
        username=user.username,
        temp_password=temp_password,
        message="Employee created successfully. Please share credentials with the employee."
    )


@router.post("/query", response_model=PaginatedResponse[EmployeeResponse])
async def query_employees(
    pagination_request: PaginationRequest,
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Query employees with pagination, filtering, and sorting.
    Uses POST method with pagination request payload.
    """
    # Build base query - exclude soft-deleted employees
    query = db.query(Employee).filter(
        Employee.company_id == current_user.company_id,
        Employee.deleted_at.is_(None)
    )
    
    # Apply pagination, filters, and sorting
    items, pagination_info = paginate_query(query, pagination_request, Employee)
    
    # Create paginated response
    return create_paginated_response(items, pagination_info, EmployeeResponse)


@router.get("/dropdown", response_model=List[EmployeeDropdownResponse])
async def get_employees_dropdown(
    search: Optional[str] = Query(None, description="Search by employee name or code"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a simplified list of active employees for dropdown selection.
    Useful for task assignment and other selection scenarios.
    
    - Returns only active, non-deleted employees ordered by name
    - Supports search by name (first_name, last_name) or employee_code
    - Limited to prevent returning huge datasets (default: 50, max: 100)
    - Use search parameter to filter results as user types
    """
    employees = EmployeeService.get_employees_for_dropdown(
        db=db,
        company_id=current_user.company_id,
        search=search,
        limit=limit
    )
    
    return [EmployeeDropdownResponse(
        id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name
    ) for emp in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee_by_id(
    employee_id: int,
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    employee = EmployeeService.get_employee_by_id(
        db,
        employee_id,
        current_user.company_id
    )
    
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee_information(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    employee = EmployeeService.update_employee(
        db,
        employee_id,
        current_user.company_id,
        employee_data
    )
    
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def deactivate_employee(
    employee_id: int,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    EmployeeService.delete_employee(
        db,
        employee_id,
        current_user.company_id
    )
    
    return MessageResponse(
        message=f"Employee {employee_id} has been deleted successfully. The email can now be reused in another company."
    )


# Attachment routes
@router.post(
    "/{employee_id}/attachments",
    response_model=EmployeeAttachmentListResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_employee_attachments(
    employee_id: int,
    files: List[UploadFile] = File(..., description="One or more files to upload"),
    attachment_type: AttachmentType = Form(..., description="Type of attachment (applies to all files)"),
    description: Optional[str] = Form(None, description="Optional description (applies to all files)"),
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Upload one or more attachments for an employee.
    
    You can upload a single file or multiple files in one request.
    All files will be uploaded with the same attachment_type and description.
    
    Supported attachment types:
    - profile_photo: Employee profile photo (images only)
    - experience_letter: Experience letters (documents)
    - aadhar_card: Aadhar card copy (documents/images)
    - education_certificate: Education certificates (documents/images)
    - pan_card: PAN card copy (documents/images)
    - passport: Passport copy (documents/images)
    - resume: Resume/CV (documents)
    - other: Other documents
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required"
        )
    
    import logging
    logger = logging.getLogger(__name__)
    
    uploaded_attachments = []
    errors = []
    
    for idx, file in enumerate(files):
        try:
            attachment = EmployeeService.upload_employee_attachment(
                db=db,
                employee_id=employee_id,
                company_id=current_user.company_id,
                file=file,
                attachment_type=attachment_type,
                description=description
            )
            
            # Add download and view URLs if using S3
            attachment_dict = EmployeeAttachmentResponse.model_validate(attachment).model_dump(exclude_none=False)
            if settings.USE_S3 and attachment.file_path.startswith("company_"):
                try:
                    download_url = get_s3_download_url(attachment.file_path)
                    view_url = get_s3_view_url(attachment.file_path, mime_type=attachment.mime_type)
                    if download_url:
                        attachment_dict["download_url"] = download_url
                    if view_url:
                        attachment_dict["view_url"] = view_url
                except Exception as e:
                    logger.error(f"Error generating S3 URLs for attachment: {str(e)}", exc_info=True)
            
            uploaded_attachments.append(EmployeeAttachmentResponse(**attachment_dict))
            
        except Exception as e:
            error_msg = f"Failed to upload file {file.filename or f'file_{idx+1}'}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
    
    if not uploaded_attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload any files. Errors: {', '.join(errors)}"
        )
    
    return EmployeeAttachmentListResponse(
        attachments=uploaded_attachments,
        total=len(uploaded_attachments)
    )


@router.get(
    "/{employee_id}/attachments",
    response_model=EmployeeAttachmentListResponse
)
async def get_employee_attachments(
    employee_id: int,
    attachment_type: Optional[AttachmentType] = Query(None, description="Filter by attachment type"),
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all attachments for an employee.
    Optionally filter by attachment type.
    """
    attachments = EmployeeService.get_employee_attachments(
        db=db,
        employee_id=employee_id,
        company_id=current_user.company_id,
        attachment_type=attachment_type
    )
    
    # Add download and view URLs for S3 files
    import logging
    logger = logging.getLogger(__name__)
    attachment_responses = []
    for att in attachments:
        att_dict = EmployeeAttachmentResponse.model_validate(att).model_dump(exclude_none=False)
        if settings.USE_S3 and att.file_path.startswith("company_"):
            try:
                download_url = get_s3_download_url(att.file_path)
                view_url = get_s3_view_url(att.file_path, mime_type=att.mime_type)
                if download_url:
                    att_dict["download_url"] = download_url
                if view_url:
                    att_dict["view_url"] = view_url
            except Exception as e:
                # Log error but don't fail the request
                logger.error(f"Error generating S3 URLs for attachment {att.id}: {str(e)}", exc_info=True)
        attachment_responses.append(EmployeeAttachmentResponse(**att_dict))
    
    return EmployeeAttachmentListResponse(
        attachments=attachment_responses,
        total=len(attachments)
    )


@router.get(
    "/{employee_id}/attachments/{attachment_id}",
    response_class=Response
)
async def download_employee_attachment(
    employee_id: int,
    attachment_id: int,
    redirect: bool = Query(False, description="If True and using S3, returns redirect URL instead of file content"),
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Download an employee attachment file.
    
    - If using S3 and redirect=True: Returns a redirect to presigned URL
    - If using S3 and redirect=False: Downloads file from S3 and returns content
    - If using local storage: Returns file content directly
    
    Returns the file with appropriate content type headers.
    """
    attachment = EmployeeService.get_employee_attachment_by_id(
        db=db,
        attachment_id=attachment_id,
        employee_id=employee_id,
        company_id=current_user.company_id
    )
    
    # Check if file is in S3
    if settings.USE_S3 and attachment.file_path.startswith("company_"):
        # Generate presigned URL for S3
        presigned_url = get_s3_download_url(attachment.file_path)
        
        if presigned_url:
            if redirect:
                # Return redirect to presigned URL
                return RedirectResponse(url=presigned_url, status_code=302)
            else:
                # Download file content from S3 and return
                file_content = get_file_content(attachment.file_path)
                if file_content:
                    return Response(
                        content=file_content,
                        media_type=attachment.mime_type,
                        headers={
                            "Content-Disposition": f'attachment; filename="{attachment.file_name}"'
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File not found in S3"
                    )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
    
    # Fallback to local storage
    file_path = get_file_path(attachment.file_path)
    
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=attachment.file_name,
        media_type=attachment.mime_type
    )


@router.delete(
    "/{employee_id}/attachments/{attachment_id}",
    response_model=MessageResponse
)
async def delete_employee_attachment(
    employee_id: int,
    attachment_id: int,
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Delete an employee attachment.
    This will delete both the database record and the physical file.
    """
    EmployeeService.delete_employee_attachment(
        db=db,
        attachment_id=attachment_id,
        employee_id=employee_id,
        company_id=current_user.company_id
    )
    
    return MessageResponse(
        message=f"Attachment {attachment_id} deleted successfully"
    )

