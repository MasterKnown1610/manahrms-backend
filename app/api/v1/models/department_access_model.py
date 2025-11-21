from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class DepartmentAccess(Base):
    """
    Department Access model for managing user permissions to view departments.
    Admins can grant or revoke access to specific users for specific departments.
    """
    __tablename__ = "department_access"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Admin who granted access
    is_active = Column(Boolean, default=True)  # Can be used to temporarily revoke access
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = relationship("Department", back_populates="access_grants")
    user = relationship("User", foreign_keys=[user_id], back_populates="department_access")
    granted_by_user = relationship("User", foreign_keys=[granted_by])
    
    # Ensure one access record per user-department combination
    __table_args__ = (
        UniqueConstraint('department_id', 'user_id', name='uq_department_user_access'),
    )
    
    def __repr__(self):
        return f"<DepartmentAccess user_id={self.user_id} department_id={self.department_id}>"

