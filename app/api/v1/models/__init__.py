"""
Models package for the HRMS application.
"""

from app.api.v1.models.company_model import Company
from app.api.v1.models.department_model import Department
from app.api.v1.models.employee_model import Employee, Gender
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.attendance_model import Attendance
from app.api.v1.models.employee_attachment_model import EmployeeAttachment, AttachmentType

__all__ = [
    "Company",
    "Department",
    "Employee",
    "Gender",
    "User",
    "UserRole",
    "Attendance",
    "EmployeeAttachment",
    "AttachmentType",
]

