"""
SuperAdmin Model - Global platform administrator, not tied to any company
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from app.db.base import Base


class SuperAdmin(Base):
    """
    SuperAdmin model for global platform management.
    SuperAdmins can manage all companies, subscriptions, and plans.
    Not tied to any specific company.
    """
    __tablename__ = "super_admins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SuperAdmin {self.username}>"
