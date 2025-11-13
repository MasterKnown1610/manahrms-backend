from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.v1.models.task_model import Task, TaskStatus, TaskPriority
from app.api.v1.models.employee_model import Employee
from app.api.v1.schemas.task_schema import TaskCreate, TaskUpdate


class TaskService:
    """
    Service class for task management operations.
    """

    @staticmethod
    def create_task(
        db: Session,
        company_id: int,
        creator_user_id: int,
        data: TaskCreate,
    ) -> Task:
        # Validate assignee belongs to company (if provided)
        if data.assigned_to_employee_id:
            assignee = db.query(Employee).filter(
                Employee.id == data.assigned_to_employee_id,
                Employee.company_id == company_id,
                Employee.is_active == True,
            ).first()
            if not assignee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned employee not found in company",
                )

        task = Task(
            company_id=company_id,
            title=data.title,
            description=data.description,
            priority=data.priority or TaskPriority.MEDIUM,
            status=TaskStatus.OPEN,
            due_date=data.due_date,
            assigned_to_employee_id=data.assigned_to_employee_id,
            created_by_user_id=creator_user_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task_by_id(db: Session, company_id: int, task_id: int) -> Task:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.company_id == company_id)
            .first()
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task

    @staticmethod
    def list_tasks(
        db: Session,
        company_id: int,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        assigned_to_employee_id: Optional[int] = None,
        only_mine_employee_id: Optional[int] = None,
    ) -> Tuple[List[Task], int]:
        query = db.query(Task).filter(Task.company_id == company_id)

        if status_filter is not None:
            query = query.filter(Task.status == status_filter)
        if priority_filter is not None:
            query = query.filter(Task.priority == priority_filter)
        if assigned_to_employee_id is not None:
            query = query.filter(Task.assigned_to_employee_id == assigned_to_employee_id)
        if only_mine_employee_id is not None:
            query = query.filter(Task.assigned_to_employee_id == only_mine_employee_id)

        total = query.count()
        items = (
            query.order_by(Task.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def update_task(
        db: Session, company_id: int, task_id: int, data: TaskUpdate
    ) -> Task:
        task = TaskService.get_task_by_id(db, company_id, task_id)

        # Validate assignee (if changed)
        if data.assigned_to_employee_id is not None:
            if data.assigned_to_employee_id:
                assignee = db.query(Employee).filter(
                    Employee.id == data.assigned_to_employee_id,
                    Employee.company_id == company_id,
                ).first()
                if not assignee:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Assigned employee not found in company",
                    )
            # allow setting to None to unassign

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def close_task(db: Session, company_id: int, task_id: int) -> Task:
        task = TaskService.get_task_by_id(db, company_id, task_id)
        task.status = TaskStatus.CLOSED
        db.commit()
        db.refresh(task)
        return task


