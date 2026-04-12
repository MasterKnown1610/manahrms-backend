import logging
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.models.task_comment_model import TaskComment
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.schemas.task_schema import TaskCommentCreate, TaskCommentUpdate

logger = logging.getLogger(__name__)


class TaskCommentService:

    @staticmethod
    def _load(db: Session, comment_id: int, task_id: int, company_id: int) -> TaskComment:
        comment = (
            db.query(TaskComment)
            .options(joinedload(TaskComment.user))
            .filter(
                TaskComment.id == comment_id,
                TaskComment.task_id == task_id,
                TaskComment.company_id == company_id,
            )
            .first()
        )
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        return comment

    @staticmethod
    def add_comment(
        db: Session,
        task_id: int,
        company_id: int,
        user_id: int,
        data: TaskCommentCreate,
    ) -> TaskComment:
        comment = TaskComment(
            task_id=task_id,
            company_id=company_id,
            user_id=user_id,
            content=data.content,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return (
            db.query(TaskComment)
            .options(joinedload(TaskComment.user))
            .filter(TaskComment.id == comment.id)
            .first()
        )

    @staticmethod
    def list_comments(db: Session, task_id: int, company_id: int) -> List[TaskComment]:
        return (
            db.query(TaskComment)
            .options(joinedload(TaskComment.user))
            .filter(TaskComment.task_id == task_id, TaskComment.company_id == company_id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )

    @staticmethod
    def update_comment(
        db: Session,
        comment_id: int,
        task_id: int,
        company_id: int,
        current_user: User,
        data: TaskCommentUpdate,
    ) -> TaskComment:
        comment = TaskCommentService._load(db, comment_id, task_id, company_id)

        # Only the author or an admin can edit
        if current_user.role != UserRole.ADMIN and comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own comments",
            )

        comment.content = data.content
        db.commit()
        db.refresh(comment)
        return (
            db.query(TaskComment)
            .options(joinedload(TaskComment.user))
            .filter(TaskComment.id == comment.id)
            .first()
        )

    @staticmethod
    def delete_comment(
        db: Session,
        comment_id: int,
        task_id: int,
        company_id: int,
        current_user: User,
    ) -> None:
        comment = TaskCommentService._load(db, comment_id, task_id, company_id)

        # Only the author or an admin can delete
        if current_user.role != UserRole.ADMIN and comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments",
            )

        db.delete(comment)
        db.commit()
        logger.info("Comment %s deleted from task %s", comment_id, task_id)
