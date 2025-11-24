from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    EMPLOYEE = "employee"


class User(Base):
    """
    User model for authentication and authorization.
    Supports both company admins and employees.
    Email is unique per company, allowing the same email to be used across different companies.
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('company_id', 'email', name='uq_user_company_email'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    force_password_change = Column(Boolean, default=False)  # For first-time employee login
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    employee = relationship("Employee", back_populates="user", foreign_keys=[employee_id])
    department_access = relationship("DepartmentAccess", foreign_keys="DepartmentAccess.user_id", back_populates="user", cascade="all, delete-orphan")
    led_projects = relationship("Project", foreign_keys="Project.project_lead_id", back_populates="project_lead")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


