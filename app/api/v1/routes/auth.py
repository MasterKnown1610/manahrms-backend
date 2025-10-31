from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.schemas.user_schema import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    MessageResponse,
    PasswordChange
)
from app.api.v1.schemas.company_schema import (
    CompanyRegister,
    CompanyRegistrationResponse
)
from app.api.v1.services.auth_service import AuthService
from app.api.v1.dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register-company", response_model=CompanyRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_company(
    company_data: CompanyRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new company with admin user.
    
    **This is the main registration endpoint for the HRMS system.**
    
    Required fields:
    - **company_name**: Company name
    - **company_email**: Company email address
    - **company_phone**: Company phone number (optional)
    - **company_address**: Company address (optional)
    - **admin_full_name**: Admin user's full name
    - **admin_email**: Admin user's email address
    - **admin_username**: Admin username for login
    - **admin_password**: Admin password (min 6 characters)
    
    Returns:
    - Company information
    - Admin username for login
    - Success message
    
    After registration:
    1. Admin can login using the provided username and password
    2. Admin can add employees to the company
    3. Admin can manage departments, attendance, payroll, etc.
    """
    company, admin_user = AuthService.register_company(db, company_data)
    
    return CompanyRegistrationResponse(
        company=company,
        admin_username=admin_user.username,
        message="Company registered successfully! Admin can now login."
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    **DEPRECATED** - Please use `/auth/register-company` endpoint instead.
    
    This endpoint is kept for backward compatibility but will return an error.
    All new registrations should use the company registration endpoint.
    """
    user = AuthService.register_user(db, user_data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login for both admin and employee users.
    
    Required fields:
    - **username**: Your username
    - **password**: Your password
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: Bearer
    - **user**: User information including role (admin/employee)
    
    Usage:
    1. Use the returned access token in subsequent requests
    2. Add to Authorization header: `Bearer <token>`
    3. Token includes role information for access control
    
    Example:
    ```
    curl -X POST "http://localhost:8000/api/v1/auth/login" \\
         -H "Content-Type: application/json" \\
         -d '{"username": "admin", "password": "password123"}'
    ```
    
    Notes:
    - Employees may be prompted to change password on first login
    - Check `force_password_change` flag in user response
    """
    user, access_token = AuthService.authenticate_user(db, login_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires authentication token in header:
    ```
    Authorization: Bearer <token>
    ```
    
    Returns:
    - User ID, username, email, full name
    - Company ID
    - Role (admin/employee)
    - Account status
    - Force password change flag
    
    Example:
    ```
    curl -H "Authorization: Bearer YOUR_TOKEN" \\
         http://localhost:8000/api/v1/auth/me
    ```
    """
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    
    Requires authentication token in header.
    
    Required fields:
    - **current_password**: Current password
    - **new_password**: New password (min 6 characters)
    - **confirm_password**: Confirm new password (must match)
    
    Usage:
    1. Employees should change password on first login
    2. Users can change password anytime for security
    3. Current password must be correct
    4. New password must be different and meet requirements
    
    Returns:
    - Success message
    
    Example:
    ```
    curl -X POST "http://localhost:8000/api/v1/auth/change-password" \\
         -H "Authorization: Bearer YOUR_TOKEN" \\
         -H "Content-Type: application/json" \\
         -d '{
           "current_password": "temp123",
           "new_password": "newSecure123",
           "confirm_password": "newSecure123"
         }'
    ```
    
    Notes:
    - Password change clears `force_password_change` flag
    - User remains logged in after password change
    - Use the same token for subsequent requests
    """
    AuthService.change_password(db, current_user, password_data)
    
    return MessageResponse(
        message="Password changed successfully"
    )
