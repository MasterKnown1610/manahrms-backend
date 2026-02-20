from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Numeric, Text, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class Gender(str, enum.Enum):
    """Gender enumeration"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Employee(Base):
    """
    Employee model for storing employee information.
    Each employee belongs to a company and optionally has a user account for portal access.
    Email is unique per company, allowing the same email to be used across different companies.
    """
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint('company_id', 'email', name='uq_employee_company_email'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    # Personal Information
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    
    # Address Information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    pin_code = Column(String(10), nullable=True)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    
    # Employment Information
    position = Column(String(255), nullable=True)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(10, 2), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="employees")
    department = relationship("Department", back_populates="employees")
    user = relationship("User", back_populates="employee", foreign_keys="User.employee_id", uselist=False)
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    leave_balances = relationship("LeaveBalance", back_populates="employee", cascade="all, delete-orphan")
    attachments = relationship("EmployeeAttachment", back_populates="employee", cascade="all, delete-orphan")
    led_projects = relationship("Project", foreign_keys="Project.project_lead_id", back_populates="project_lead")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Employee {self.employee_code} - {self.full_name}>"

