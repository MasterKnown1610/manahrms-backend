from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import timedelta

from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.company_model import Company, CompanyType
from app.api.v1.schemas.user_schema import UserLogin, PasswordChange
from app.api.v1.schemas.company_schema import CompanyRegister
from app.core.security import hash_password_for_storage, verify_password_against_hash, create_jwt_access_token
from app.core.config import settings


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
    def register_company_with_admin_user(db: Session, company_data: CompanyRegister) -> tuple[Company, User]:
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
    def authenticate_user_and_generate_token(db: Session, login_data: UserLogin) -> tuple[User, str]:
        user = db.query(User).filter(User.username == login_data.username).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password_against_hash(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        if not user.company.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company account is inactive"
            )
        
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
        
        return user, access_token
    
    @staticmethod
    def change_user_password(db: Session, user: User, password_data: PasswordChange) -> None:
        if not verify_password_against_hash(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
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
