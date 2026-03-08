from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_database_session
from app.core.security import decode_and_verify_jwt_token
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.subscription_model import CompanySubscription, SubscriptionStatus
from app.core.config import settings

# OAuth2 password bearer token scheme for FastAPI docs integration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token",
    scheme_name="OAuth2PasswordBearer"
)


def get_current_authenticated_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_database_session)
) -> User:
    
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
    
    # Check subscription status - if expired, block access
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.company_id == user.company_id
    ).first()
    
    if subscription:
        now = datetime.utcnow()
        
        # Check if subscription is expired or cancelled
        if subscription.status in [SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED]:
            # If cancelled, check if period has ended
            if subscription.status == SubscriptionStatus.CANCELLED:
                if subscription.current_period_end and subscription.current_period_end.replace(tzinfo=None) < now:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "success": False,
                            "message": "Your subscription has expired. Please renew to continue using the service.",
                            "error_code": "SUBSCRIPTION_EXPIRED"
                        }
                    )
            else:
                # Status is EXPIRED
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": "Your subscription has expired. Please renew to continue using the service.",
                        "error_code": "SUBSCRIPTION_EXPIRED"
                    }
                )
        
        # Check if current_period_end has passed (subscription expired)
        if subscription.current_period_end:
            if subscription.current_period_end.replace(tzinfo=None) < now:
                # Update status to expired if not already
                if subscription.status not in [SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED]:
                    subscription.status = SubscriptionStatus.EXPIRED
                    db.commit()
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": "Your subscription has expired. Please renew to continue using the service.",
                        "error_code": "SUBSCRIPTION_EXPIRED"
                    }
                )
        
        # Check if trial has ended without activation
        if subscription.status == SubscriptionStatus.TRIAL and subscription.trial_end:
            if subscription.trial_end.replace(tzinfo=None) < now:
                # Trial expired, update status
                subscription.status = SubscriptionStatus.EXPIRED
                db.commit()
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": "Your trial period has expired. Please subscribe to continue using the service.",
                        "error_code": "SUBSCRIPTION_EXPIRED"
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


def get_current_authenticated_user_allow_expired(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_database_session)
) -> User:
    """
    Get current authenticated user but allow access even if subscription is expired.
    This is used for endpoints that should be accessible even with expired subscription,
    such as subscription creation/renewal.
    """
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
    
    # Note: We don't check subscription status here - this allows expired subscriptions
    # to access endpoints like subscription creation/renewal
    
    return user


