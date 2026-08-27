from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from datetime import timedelta
import logging

from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.company_model import Company, CompanyType
from app.api.v1.schemas.user_schema import UserLogin, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest
from app.api.v1.schemas.company_schema import CompanyRegister
from app.core.security import hash_password_for_storage, verify_password_against_hash, create_jwt_access_token, decode_and_verify_jwt_token
from app.core.config import settings
from app.api.v1.utils.error_handler import raise_http_exception

logger = logging.getLogger(__name__)


def generate_unique_company_code(db: Session) -> str:
    last_company = db.query(Company).order_by(Company.id.desc()).first()
    
    if last_company and last_company.company_code:
        try:
            last_num = int(last_company.company_code.replace("CMP", ""))
            new_num = last_num + 1
        except (ValueError, AttributeError):
            new_num = 1
    else:
        new_num = 1
    
    return f"CMP{new_num:08d}"


class AuthService:
    
    @staticmethod
    def register_company_with_admin_user(db: Session, company_data: CompanyRegister) -> tuple[Company, User, bool]:
        existing_company = db.query(Company).filter(
            Company.email == company_data.company_email
        ).first()
        if existing_company:
            raise_http_exception(
                message="Company email already registered",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="COMPANY_EMAIL_EXISTS"
            )
        
        # Check if admin username already exists (username is globally unique)
        existing_username = db.query(User).filter(
            User.username == company_data.admin_username
        ).first()
        if existing_username:
            raise_http_exception(
                message="Username already taken",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="USERNAME_EXISTS"
            )
        
        # Note: Admin email uniqueness is enforced per company via database constraint
        # Since we're creating a new company, there won't be any users with this company_id yet,
        # so no need to check email uniqueness here
        
        try:
            company_code = generate_unique_company_code(db)
            
            # Ensure uniqueness (retry if conflict)
            max_attempts = 10
            attempt = 0
            while db.query(Company).filter(Company.company_code == company_code).first() and attempt < max_attempts:
                # Extract number and increment
                try:
                    num = int(company_code.replace("CMP", ""))
                    num += 1
                    company_code = f"CMP{num:08d}"
                except ValueError:
                    company_code = generate_unique_company_code(db)
                attempt += 1
            
            # Get company_type - use the value string directly since database enum uses string values
            # Map schema enum to model enum, then use the value
            company_type_map = {
                "Solo Proprietor": CompanyType.SOLO_PROPRIETOR,
                "Organization": CompanyType.ORGANIZATION,
                "Private Limited": CompanyType.PRIVATE_LIMITED,
                "LLP": CompanyType.LLP,
                "Partnership": CompanyType.PARTNERSHIP,
                "Public Limited": CompanyType.PUBLIC_LIMITED,
                "Other": CompanyType.OTHER,
            }
            company_type_enum = company_type_map.get(company_data.company_type.value, CompanyType.OTHER)
            
            # Create company - pass enum value as string to match database enum
            new_company = Company(
                company_code=company_code,
                company_name=company_data.company_name,
                email=company_data.company_email,
                phone=company_data.company_phone,
                address=company_data.company_address,
                company_type=company_type_enum.value,  # Pass string value to match DB enum
                company_type_other=company_data.company_type_other if company_data.company_type.value == "Other" else None,
                gst_number=company_data.company_gst_number,
                pan_number=company_data.company_pan_number,
                is_active=True
            )
            db.add(new_company)
            db.flush()  # Get company ID without committing
            
            # Create admin user
            hashed_password = hash_password_for_storage(company_data.company_password)
            admin_user = User(
                company_id=new_company.id,
                email=company_data.admin_email,
                username=company_data.admin_username,
                full_name=company_data.admin_full_name,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                permissions=None,
                is_active=True,
                is_superuser=False,
                force_password_change=False
            )
            db.add(admin_user)
            
            db.commit()
            db.refresh(new_company)
            db.refresh(admin_user)

            welcome_email_sent = False
            try:
                from app.api.v1.services.mail_service import MailService

                welcome_email_sent = MailService.send_registration_welcome(
                    to_email=company_data.admin_email,
                    admin_name=company_data.admin_full_name,
                    company_name=new_company.company_name,
                    company_code=new_company.company_code or "",
                    company_email=company_data.company_email,
                    admin_email=company_data.admin_email,
                    username=company_data.admin_username,
                )
                if not welcome_email_sent:
                    logger.warning(
                        "Welcome email was not sent to %s; see SMTP logs above.",
                        company_data.admin_email,
                    )
            except Exception as email_exc:
                logger.warning(
                    "Welcome email error for %s: %s",
                    company_data.admin_email,
                    email_exc,
                )

            # Sync company to vector database
            try:
                from app.api.v1.services.vector_sync_service import VectorSyncService
                import logging
                logger = logging.getLogger(__name__)
                sync_service = VectorSyncService()
                sync_service.sync_company(db, new_company.id)
            except Exception as e:
                logger.error(f"Failed to sync company {new_company.id} to vector store: {str(e)}")
                # Don't fail the main operation if vector sync fails
            
            return new_company, admin_user, welcome_email_sent

        except Exception as e:
            db.rollback()
            raise_http_exception(
                message=f"Failed to register company: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="REGISTRATION_FAILED"
            )
    
    @staticmethod
    def authenticate_user_and_generate_token(db: Session, login_data: UserLogin) -> tuple[User, str]:
        logger.info(f"Login attempt for username/email: {login_data.username}")
        
        try:
            identifier = (login_data.username or "").strip()
            identifier_lower = identifier.lower()

            # Email is unique per company, not globally. Check every match
            # and accept the account whose password is correct.
            candidates = (
                db.query(User)
                .options(joinedload(User.company))
                .filter(
                    or_(
                        func.lower(User.username) == identifier_lower,
                        func.lower(User.email) == identifier_lower,
                        User.employee_id.in_(
                            db.query(Employee.id).filter(
                                func.lower(Employee.employee_code) == identifier_lower
                            )
                        ),
                    )
                )
                .all()
            )

            user = None
            for candidate in candidates:
                if verify_password_against_hash(login_data.password, candidate.hashed_password):
                    user = candidate
                    break

            logger.debug(
                "User query completed. Candidates=%s matched=%s",
                len(candidates),
                user is not None,
            )

            if not user:
                logger.warning(f"Login failed: No matching account for username/email: {login_data.username}")
                raise_http_exception(
                    message="Incorrect username or password",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    error_code="INVALID_CREDENTIALS"
                )
            
            logger.debug(f"User found: id={user.id}, username={user.username}, email={user.email}, is_active={user.is_active}")
            logger.debug("Password verification successful")
            
            if not user.is_active:
                logger.warning(f"Login failed: Inactive user account: {user.username}")
                raise_http_exception(
                    message="Inactive user account",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="USER_INACTIVE"
                )
            
            # Check if company relationship is loaded
            if not hasattr(user, 'company') or user.company is None:
                logger.error(f"Login failed: Company relationship not loaded for user: {user.username}, company_id: {user.company_id}")
                raise_http_exception(
                    message="Company information not found",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_code="COMPANY_NOT_FOUND"
                )
            
            logger.debug(f"Company loaded: id={user.company.id}, name={user.company.company_name}, is_active={user.company.is_active}")
            
            if not user.company.is_active:
                logger.warning(f"Login failed: Inactive company account: {user.company.company_name} (id: {user.company.id})")
                raise_http_exception(
                    message="Company account is inactive",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="COMPANY_INACTIVE"
                )
            
            logger.debug(f"Generating JWT token for user: {user.username}, company_id: {user.company_id}, role: {user.role.value}")
            
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_jwt_access_token(
                data={
                    "sub": user.username, 
                    "user_id": user.id,
                    "company_id": user.company_id,
                    "role": user.role.value
                },
                expires_delta=access_token_expires
            )
            
            logger.info(f"Login successful for user: {user.username} (id: {user.id})")
            
            return user, access_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login for username/email: {login_data.username}", exc_info=True)
            raise
    
    @staticmethod
    def change_user_password(db: Session, user: User, password_data: PasswordChange) -> None:
        if not verify_password_against_hash(password_data.current_password, user.hashed_password):
            raise_http_exception(
                message="Current password is incorrect",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_CURRENT_PASSWORD"
            )
        
        user.hashed_password = hash_password_for_storage(password_data.new_password)
        user.force_password_change = False
        
        db.commit()
        db.refresh(user)
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        return db.query(User).filter(User.id == user_id).first()

    # ------------------------------------------------------------------ #
    #  Forgot / Reset password                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def request_password_reset(db: Session, request: ForgotPasswordRequest) -> bool:
        """
        Look up the user by email, generate a short-lived JWT reset token,
        and dispatch the reset email.  Always returns True so callers cannot
        use the response to enumerate valid email addresses.
        """
        user = db.query(User).filter(User.email == request.email).first()

        if not user or not user.is_active:
            # Silently succeed — don't reveal whether the address exists.
            logger.info("Password reset requested for unknown/inactive email: %s", request.email)
            return True

        reset_token = create_jwt_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "purpose": "password_reset",
            },
            expires_delta=timedelta(hours=1),
        )

        try:
            from app.api.v1.services.mail_service import MailService
            from app.core.config import settings

            reset_url = (settings.APP_PUBLIC_URL or "").strip().rstrip("/")
            reset_url = f"{reset_url}/reset-password?token={reset_token}" if reset_url else f"/reset-password?token={reset_token}"

            sent = MailService.send_password_reset_email(
                to_email=user.email,
                full_name=user.full_name,
                reset_url=reset_url,
            )
            if not sent:
                logger.warning("Password reset email not sent to %s", user.email)
        except Exception as exc:
            logger.error("Error sending password reset email to %s: %s", user.email, exc)

        return True

    @staticmethod
    def reset_password_with_token(db: Session, request: ResetPasswordRequest) -> None:
        """
        Validate the reset token and update the user's password.
        Raises HTTP 400 for invalid/expired tokens.
        """
        payload = decode_and_verify_jwt_token(request.token)

        if not payload or payload.get("purpose") != "password_reset":
            raise_http_exception(
                message="Invalid or expired password reset link",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_RESET_TOKEN",
            )

        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()

        if not user or not user.is_active:
            raise_http_exception(
                message="Invalid or expired password reset link",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_RESET_TOKEN",
            )

        user.hashed_password = hash_password_for_storage(request.new_password)
        user.force_password_change = False
        db.commit()
        db.refresh(user)
        logger.info("Password reset successfully for user id=%s", user.id)
