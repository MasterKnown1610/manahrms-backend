from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class TaskCommit(Base):
    """
    Stores git commit / branch info linked to a task.
    Multiple commits and branches can be associated with one task.
    """
    __tablename__ = "task_commits"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Git fields
    branch = Column(String(255), nullable=True)
    commit_hash = Column(String(100), nullable=True)
    commit_message = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    commit_url = Column(String(500), nullable=True)
    committed_at = Column(DateTime, nullable=True)

    # Who added this record
    added_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="commits")
    added_by = relationship("User")

    def __repr__(self):
        return f"<TaskCommit id={self.id} task_id={self.task_id} branch={self.branch}>"
