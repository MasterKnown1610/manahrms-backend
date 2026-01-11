from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class AttachmentType(str, enum.Enum):
    """Types of employee attachments"""
    PROFILE_PHOTO = "profile_photo"
    EXPERIENCE_LETTER = "experience_letter"
    AADHAR_CARD = "aadhar_card"
    EDUCATION_CERTIFICATE = "education_certificate"
    PAN_CARD = "pan_card"
    PASSPORT = "passport"
    RESUME = "resume"
    OTHER = "other"


class EmployeeAttachment(Base):
    """
    Employee attachment model for storing file metadata.
    Stores references to uploaded files (profile photos, documents, certificates, etc.)
    """
    __tablename__ = "employee_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File information
    attachment_type = Column(Enum(AttachmentType), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(500), nullable=False)  # Path relative to upload directory
    file_size = Column(Integer, nullable=False)  # File size in bytes
    mime_type = Column(String(100), nullable=False)  # e.g., "image/jpeg", "application/pdf"
    
    # Optional metadata
    description = Column(Text, nullable=True)  # Optional description/notes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    employee = relationship("Employee", back_populates="attachments")
    
    def __repr__(self):
        return f"<EmployeeAttachment {self.id} - {self.attachment_type.value} for employee {self.employee_id}>"
