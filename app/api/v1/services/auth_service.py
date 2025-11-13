from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import timedelta

from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.company_model import Company, CompanyType
from app.api.v1.schemas.user_schema import UserLogin, PasswordChange
from app.api.v1.schemas.company_schema import CompanyRegister
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings


def generate_company_code(db: Session) -> str:
    """Generate a unique company code in format CMP00000001"""
    # Find the highest existing company code number
    last_company = db.query(Company).order_by(Company.id.desc()).first()
    
    if last_company and last_company.company_code:
        # Extract number from existing code
        try:
            last_num = int(last_company.company_code.replace("CMP", ""))
            new_num = last_num + 1
        except (ValueError, AttributeError):
            new_num = 1
    else:
        new_num = 1
    
    # Format as CMP00000001 (8 digits)
    return f"CMP{new_num:08d}"


class AuthService:
    """
    Service class for authentication operations.
    Handles company registration, user authentication, and password management.
    """
    
    @staticmethod
    def register_company(db: Session, company_data: CompanyRegister) -> tuple[Company, User]:
        """
        Register a new company with admin user.
        
        Args:
            db: Database session
            company_data: Company registration data including admin details
            
        Returns:
            Tuple of (company object, admin user object)
            
        Raises:
            HTTPException: If company email, username, or admin email already exists
        """
        # Check if company email already exists
        existing_company = db.query(Company).filter(
            Company.email == company_data.company_email
        ).first()
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company email already registered"
            )
        
        # Check if admin username already exists
        existing_username = db.query(User).filter(
            User.username == company_data.admin_username
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Check if admin email already exists
        existing_admin_email = db.query(User).filter(
            User.email == company_data.admin_email
        ).first()
        if existing_admin_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin email already registered"
            )
        
        try:
            # Generate company code
            company_code = generate_company_code(db)
            
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
                    company_code = generate_company_code(db)
                attempt += 1
            
            # Convert company_type enum to model enum
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
            
            # Create company
            new_company = Company(
                company_code=company_code,
                company_name=company_data.company_name,
                email=company_data.company_email,
                phone=company_data.company_phone,
                address=company_data.company_address,
                company_type=company_type_enum,
                company_type_other=company_data.company_type_other if company_data.company_type.value == "Other" else None,
                gst_number=company_data.company_gst_number,
                pan_number=company_data.company_pan_number,
                is_active=True
            )
            db.add(new_company)
            db.flush()  # Get company ID without committing
            
            # Create admin user
            hashed_password = get_password_hash(company_data.company_password)
            admin_user = User(
                company_id=new_company.id,
                email=company_data.admin_email,
                username=company_data.admin_username,
                full_name=company_data.admin_full_name,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=False,
                force_password_change=False
            )
            db.add(admin_user)
            
            db.commit()
            db.refresh(new_company)
            db.refresh(admin_user)
            
            return new_company, admin_user
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register company: {str(e)}"
            )
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> tuple[User, str]:
        """
        Authenticate a user (admin or employee) and generate access token.
        
        Args:
            db: Database session
            login_data: User login credentials
            
        Returns:
            Tuple of (user object, access token)
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Find user by username
        user = db.query(User).filter(User.username == login_data.username).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        # Check if company is active
        if not user.company.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company account is inactive"
            )
        
        # Create access token with role information
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username, 
                "user_id": user.id,
                "company_id": user.company_id,
                "role": user.role.value
            },
            expires_delta=access_token_expires
        )
        
        return user, access_token
    
    @staticmethod
    def change_password(db: Session, user: User, password_data: PasswordChange) -> None:
        """
        Change user password.
        
        Args:
            db: Database session
            user: Current user object
            password_data: Password change data
            
        Raises:
            HTTPException: If current password is incorrect
        """
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.force_password_change = False  # Reset force change flag
        
        db.commit()
        db.refresh(user)
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        """
        Get user by username.
        
        Args:
            db: Database session
            username: Username to search for
            
        Returns:
            User object or None
        """
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User ID to search for
            
        Returns:
            User object or None
        """
        return db.query(User).filter(User.id == user_id).first()
