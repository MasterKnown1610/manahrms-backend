from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    """
    Task model for assigning and tracking tasks within a company.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.OPEN, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    due_date = Column(Date, nullable=True)

    assigned_to_employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Workflow fields
    project_workflow_id = Column(UUID(as_uuid=True), ForeignKey("project_workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    current_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company")
    assigned_to_employee = relationship("Employee")
    created_by_user = relationship("User")
    project = relationship("Project", back_populates="tasks")
    project_workflow = relationship("ProjectWorkflow", back_populates="tasks")
    current_node = relationship("WorkflowNode", foreign_keys=[current_node_id])
    state_history = relationship("TaskStateHistory", back_populates="task", cascade="all, delete-orphan", order_by="TaskStateHistory.created_at")
    sla_tracking = relationship("TaskSLATracking", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task {self.id} {self.title} ({self.status})>"


