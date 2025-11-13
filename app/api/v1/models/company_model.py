from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
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
    company_type = Column(Enum(CompanyType), nullable=False)
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
    
    def __repr__(self):
        return f"<Company {self.company_name}>"

