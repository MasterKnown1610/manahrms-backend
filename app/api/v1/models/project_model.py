from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Numeric, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Project(Base):
    """
    Project model for managing projects within a company.
    Projects have a lead, client, timeline, and associated tasks.
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    client = Column(String(255), nullable=False)
    number_of_days = Column(Integer, nullable=False)  # Expected duration in days
    target_date = Column(Date, nullable=False, index=True)  # Project deadline
    project_lead_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="projects")
    project_lead = relationship("User", foreign_keys=[project_lead_id], back_populates="led_projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project {self.name} - {self.client}>"

