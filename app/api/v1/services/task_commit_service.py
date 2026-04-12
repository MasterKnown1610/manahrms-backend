import logging
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.models.task_commit_model import TaskCommit
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.schemas.task_schema import TaskCommitCreate

logger = logging.getLogger(__name__)


class TaskCommitService:

    @staticmethod
    def add_commit(
        db: Session,
        task_id: int,
        company_id: int,
        added_by_user_id: int,
        data: TaskCommitCreate,
    ) -> TaskCommit:
        commit = TaskCommit(
            task_id=task_id,
            company_id=company_id,
            branch=data.branch,
            commit_hash=data.commit_hash,
            commit_message=data.commit_message,
            author_name=data.author_name,
            commit_url=data.commit_url,
            committed_at=data.committed_at,
            added_by_user_id=added_by_user_id,
        )
        db.add(commit)
        db.commit()
        db.refresh(commit)
        return (
            db.query(TaskCommit)
            .options(joinedload(TaskCommit.added_by))
            .filter(TaskCommit.id == commit.id)
            .first()
        )

    @staticmethod
    def list_commits(db: Session, task_id: int, company_id: int) -> List[TaskCommit]:
        return (
            db.query(TaskCommit)
            .options(joinedload(TaskCommit.added_by))
            .filter(TaskCommit.task_id == task_id, TaskCommit.company_id == company_id)
            .order_by(TaskCommit.created_at.asc())
            .all()
        )

    @staticmethod
    def delete_commit(
        db: Session,
        commit_id: int,
        task_id: int,
        company_id: int,
        current_user: User,
    ) -> None:
        commit = (
            db.query(TaskCommit)
            .filter(
                TaskCommit.id == commit_id,
                TaskCommit.task_id == task_id,
                TaskCommit.company_id == company_id,
            )
            .first()
        )
        if not commit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commit record not found")

        # Only the adder or an admin can delete
        if current_user.role != UserRole.ADMIN and commit.added_by_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only remove commit records you added",
            )

        db.delete(commit)
        db.commit()
        logger.info("Commit record %s removed from task %s", commit_id, task_id)
