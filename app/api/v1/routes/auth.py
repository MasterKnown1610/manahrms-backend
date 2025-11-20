from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_database_session
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
from app.api.v1.dependencies import get_current_authenticated_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register-company", response_model=CompanyRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_new_company_with_admin(
    company_data: CompanyRegister,
    db: Session = Depends(get_database_session)
):
    company, admin_user = AuthService.register_company_with_admin_user(db, company_data)
    
    return CompanyRegistrationResponse(
        company=company,
        admin_username=admin_user.username,
        message="Company registered successfully! Admin can now login."
    )


@router.post("/login", response_model=TokenResponse)
async def authenticate_user_and_get_token(
    login_data: UserLogin,
    db: Session = Depends(get_database_session)
):
    user, access_token = AuthService.authenticate_user_and_generate_token(db, login_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_authenticated_user_info(
    current_user = Depends(get_current_authenticated_user)
):
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_current_user_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    AuthService.change_user_password(db, current_user, password_data)
    
    return MessageResponse(
        message="Password changed successfully"
    )
