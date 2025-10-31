from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_access_token
from app.api.v1.models.user_model import User, UserRole


# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Validates JWT token and returns the authenticated user.
    Checks both user and company active status.
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}
    
    Raises:
        HTTPException: If token is invalid, user not found, or account inactive
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get username from token
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Check if company is active
    if not user.company.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company account is inactive"
        )
    
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to require admin role.
    
    Only users with role=ADMIN can access endpoints using this dependency.
    Automatically includes company isolation (admin can only manage their own company).
    
    Usage:
        @router.post("/admin-only")
        def admin_route(current_user: User = Depends(require_admin)):
            return {"message": "Admin access granted"}
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Only company admins can perform this action."
        )
    return current_user


def require_employee(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to require employee role.
    
    Only users with role=EMPLOYEE can access endpoints using this dependency.
    
    Usage:
        @router.get("/employee-portal")
        def employee_route(current_user: User = Depends(require_employee)):
            return {"message": "Employee access granted"}
    
    Raises:
        HTTPException: If user is not an employee
    """
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required"
        )
    return current_user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if current user is a superuser.
    
    This is for system-level super admins (rarely used).
    Most admin operations should use require_admin instead.
    
    Usage:
        @router.get("/superadmin")
        def superadmin_route(current_user: User = Depends(get_current_active_superuser)):
            return {"message": "Superuser access granted"}
    
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user


