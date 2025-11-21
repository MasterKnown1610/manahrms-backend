from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.core.security import decode_and_verify_jwt_token
from app.api.v1.models.user_model import User, UserRole


# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_database_session)
) -> User:
    token = credentials.credentials
    
    payload = decode_and_verify_jwt_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Could not validate credentials",
                "error_code": "INVALID_TOKEN"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Could not validate credentials",
                "error_code": "INVALID_TOKEN_PAYLOAD"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "User not found",
                "error_code": "USER_NOT_FOUND"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Inactive user account",
                "error_code": "USER_INACTIVE"
            }
        )
    
    if not user.company.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Company account is inactive",
                "error_code": "COMPANY_INACTIVE"
            }
        )
    
    return user


def require_admin_role(
    current_user: User = Depends(get_current_authenticated_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Admin access required. Only company admins can perform this action.",
                "error_code": "ADMIN_ACCESS_REQUIRED"
            }
        )
    return current_user


def require_employee_role(
    current_user: User = Depends(get_current_authenticated_user),
) -> User:
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Employee access required",
                "error_code": "EMPLOYEE_ACCESS_REQUIRED"
            }
        )
    return current_user


def require_superuser_role(
    current_user: User = Depends(get_current_authenticated_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Superuser privileges required",
                "error_code": "SUPERUSER_ACCESS_REQUIRED"
            }
        )
    return current_user


