from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Employee(Base):
    """
    Employee model for storing employee information.
    Each employee belongs to a company and optionally has a user account for portal access.
    """
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    # Personal Information
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    # Employment Information
    position = Column(String(255), nullable=True)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(10, 2), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="employees")
    department = relationship("Department", back_populates="employees")
    user = relationship("User", back_populates="employee", foreign_keys="User.employee_id", uselist=False)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Employee {self.employee_code} - {self.full_name}>"

