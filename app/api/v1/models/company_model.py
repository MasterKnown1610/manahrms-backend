from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from datetime import datetime
import enum

from app.db.base import Base


class CompanyType(str, enum.Enum):
    """Company type enumeration"""
    SOLO_PROPRIETOR = "Solo Proprietor"
    ORGANIZATION = "Organization"
    PRIVATE_LIMITED = "Private Limited"
    LLP = "LLP"
    PARTNERSHIP = "Partnership"
    PUBLIC_LIMITED = "Public Limited"
    OTHER = "Other"


class CompanyTypeEnum(TypeDecorator):
    """Custom type decorator to handle CompanyType enum conversion"""
    impl = ENUM
    cache_ok = True
    
    def __init__(self):
        super().__init__(
            'Solo Proprietor', 'Organization', 'Private Limited', 'LLP', 
            'Partnership', 'Public Limited', 'Other',
            name='companytype',
            create_type=False
        )
    
    def process_bind_param(self, value, dialect):
        """Convert enum to string value for database"""
        if value is None:
            return None
        if isinstance(value, CompanyType):
            return value.value
        if isinstance(value, str):
            return value
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert database string to enum"""
        if value is None:
            return None
        # Return as string - let the application handle enum conversion if needed
        return value


class Company(Base):
    """
    Company model for multi-tenant HRMS system.
    Each company is a separate tenant with its own employees and data.
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    company_code = Column(String(50), unique=True, index=True, nullable=False)
    company_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    company_type = Column(CompanyTypeEnum(), nullable=False)
    company_type_other = Column(String(255), nullable=True)  # Custom type when "Other" is selected
    gst_number = Column(String(50), nullable=True, index=True)
    pan_number = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company {self.company_name}>"

