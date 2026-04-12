from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class TaskPermission(Base):
    """
    Grants a non-admin user (employee) the ability to create and assign tasks,
    just like an admin. Admins manage this table.
    """
    __tablename__ = "task_permissions"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_task_permission_company_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])

    def __repr__(self):
        return f"<TaskPermission user_id={self.user_id} company_id={self.company_id}>"
