from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Date
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
    Supports unlimited hierarchy: a task can have subtasks (1 → 1.1 → 1.1.1 …).
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

    # Hierarchy: self-referential parent → child relationship
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    # Display order within the same parent (0-based; converted to 1-based in task_number)
    position = Column(Integer, default=0, nullable=False, server_default="0")

    # Primary branch for the task (e.g. feature/task-42)
    branch = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Flat relationships ──────────────────────────────────────────
    company = relationship("Company")
    assigned_to_employee = relationship("Employee")
    created_by_user = relationship("User")
    project = relationship("Project", back_populates="tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan", order_by="TaskComment.created_at")
    commits = relationship("TaskCommit", back_populates="task", cascade="all, delete-orphan", order_by="TaskCommit.created_at")

    # ── Hierarchy relationships ─────────────────────────────────────
    # `remote_side=[id]` makes this side the "one" (parent); foreign_keys on child side
    parent = relationship(
        "Task",
        back_populates="subtasks",
        remote_side=[id],
        foreign_keys=[parent_task_id],
    )
    subtasks = relationship(
        "Task",
        back_populates="parent",
        foreign_keys=[parent_task_id],
        order_by="Task.position",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Task {self.id} {self.title} ({self.status})>"


