from sqlalchemy.ext.declarative import declarative_base

# Create Base class for all models
Base = declarative_base()

# Import all models here so they are registered with Base
# This ensures tables are created when Base.metadata.create_all() is called
# Import order matters due to foreign key relationships

from app.api.v1.models.company_model import Company  # noqa
from app.api.v1.models.department_model import Department  # noqa
from app.api.v1.models.department_access_model import DepartmentAccess  # noqa
from app.api.v1.models.employee_model import Employee  # noqa
from app.api.v1.models.user_model import User  # noqa
from app.api.v1.models.project_model import Project  # noqa
from app.api.v1.models.task_model import Task  # noqa
from app.api.v1.models.attendance_model import Attendance  # noqa
from app.api.v1.models.employee_attachment_model import EmployeeAttachment  # noqa
from app.api.v1.models.vector_store_model import VectorStore  # noqa
from app.api.v1.models.leave_model import LeaveType, LeaveRequest, LeaveBalance  # noqa
from app.api.v1.models.chat_model import ChatRoom, ChatRoomMember, ChatMessage  # noqa
from app.api.v1.models.meeting_model import Meeting, MeetingParticipant  # noqa
from app.api.v1.models.event_model import Event, EventParticipant  # noqa
