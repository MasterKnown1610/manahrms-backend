from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
import logging

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

logger = logging.getLogger(__name__)

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


@router.post("/token", response_model=dict, include_in_schema=True)
async def oauth2_token_endpoint(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_database_session)
):
    """
    OAuth2 password flow token endpoint for FastAPI docs authentication.
    This endpoint accepts form data (username and password) and returns an access token.
    Used by FastAPI's interactive docs for authentication.
    """
    logger.info(f"OAuth2 token endpoint called - IP: {request.client.host if request.client else 'unknown'}, Username: {username}")
    
    try:
        # Create UserLogin object from form data
        login_data = UserLogin(username=username, password=password)
        user, access_token = AuthService.authenticate_user_and_generate_token(db, login_data)
        
        logger.debug(f"OAuth2 token generated successfully for user: {user.username}")
        
        # Return OAuth2-compliant response (just access_token and token_type)
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException as e:
        logger.warning(f"OAuth2 token endpoint failed with HTTPException: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"OAuth2 token endpoint failed with unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Could not validate credentials",
                "error_code": "INVALID_CREDENTIALS"
            }
        )


@router.post("/login", response_model=TokenResponse)
async def authenticate_user_and_get_token(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_database_session)
):
    """
    Standard login endpoint that accepts JSON and returns token with user info.
    Use this endpoint for programmatic authentication.
    """
    logger.info(f"Login API called - IP: {request.client.host if request.client else 'unknown'}, Username: {login_data.username}")
    
    try:
        user, access_token = AuthService.authenticate_user_and_generate_token(db, login_data)
        
        logger.debug(f"Token generated successfully for user: {user.username}")
        
        response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
        logger.info(f"Login API completed successfully for user: {user.username}")
        return response
        
    except HTTPException as e:
        logger.warning(f"Login API failed with HTTPException: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Login API failed with unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


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
