from sqlalchemy import Column, Integer, DateTime, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, date

from app.db.base import Base


class Attendance(Base):
    """
    Attendance model for tracking employee punch in/out times.
    Each record represents a single day's attendance for an employee.
    """
    __tablename__ = "attendances"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Date for this attendance record
    attendance_date = Column(Date, nullable=False, index=True)
    
    # Punch in/out times
    punch_in_time = Column(DateTime, nullable=True)
    punch_out_time = Column(DateTime, nullable=True)
    
    # Work duration (calculated in hours, stored for quick access)
    work_duration_hours = Column(Integer, nullable=True)  # Duration in minutes
    
    # Status flags
    is_present = Column(Boolean, default=False)  # True if employee punched in today
    is_checked_out = Column(Boolean, default=False)  # True if employee punched out
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    employee = relationship("Employee")
    
    def __repr__(self):
        return f"<Attendance {self.employee_id} - {self.attendance_date} ({'Present' if self.is_present else 'Absent'})>"
    
    def calculate_work_duration(self):
        """Calculate work duration in minutes if both punch in and out times exist"""
        if self.punch_in_time and self.punch_out_time:
            duration = self.punch_out_time - self.punch_in_time
            return int(duration.total_seconds() / 60)  # Return minutes
        return None

