from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
import logging

from app.api.v1.models.task_model import Task, TaskStatus, TaskPriority
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.project_model import Project
from app.api.v1.schemas.task_schema import TaskCreate, TaskUpdate, SubtaskCreate
from app.api.v1.services.vector_sync_service import VectorSyncService

logger = logging.getLogger(__name__)


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
        
        # Validate project belongs to company (if provided)
        if data.project_id:
            project = db.query(Project).filter(
                Project.id == data.project_id,
                Project.company_id == company_id,
                Project.is_active == True,
            ).first()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found in company",
                )

        # Validate parent task if provided
        parent_task_id = getattr(data, "parent_task_id", None)
        if parent_task_id:
            parent = db.query(Task).filter(
                Task.id == parent_task_id,
                Task.company_id == company_id,
            ).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent task not found")

        position = TaskService._next_position(db, company_id, parent_task_id)

        task = Task(
            company_id=company_id,
            title=data.title,
            description=data.description,
            priority=data.priority or TaskPriority.MEDIUM,
            status=TaskStatus.OPEN,
            due_date=data.due_date,
            assigned_to_employee_id=data.assigned_to_employee_id,
            project_id=data.project_id,
            created_by_user_id=creator_user_id,
            parent_task_id=parent_task_id,
            position=position,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Sync to vector database
        try:
            sync_service = VectorSyncService()
            sync_service.sync_task(db, task.id)
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to vector store: {str(e)}")
            # Don't fail the main operation if vector sync fails
        
        # Emit WebSocket event if task is assigned to an employee
        if task.assigned_to_employee_id:
            try:
                from app.api.v1.services.websocket_service import websocket_service
                from app.api.v1.models.user_model import User
                from app.api.v1.utils.websocket_helper import emit_websocket_event_async
                
                # Get creator user info
                creator_user = db.query(User).filter(User.id == creator_user_id).first()
                creator_name = creator_user.full_name if creator_user else "Admin"
                
                # Get user_id from employee_id (User.employee_id references Employee.id)
                assigned_user = db.query(User).filter(
                    User.employee_id == task.assigned_to_employee_id,
                    User.company_id == company_id
                ).first()
                
                if assigned_user:
                    # User exists, send notification to that user
                    emit_websocket_event_async(
                        websocket_service.emit_task_assigned(
                            db=db,
                            tenant_id=company_id,
                            task_id=task.id,
                            task_name=task.title,
                            assigned_to=assigned_user.id,  # Use user_id
                            assigned_by=creator_user_id,
                            assigned_by_name=creator_name
                        )
                    )
                else:
                    # Employee doesn't have a user account yet, log but don't fail
                    logger.info(f"Task {task.id} assigned to employee {task.assigned_to_employee_id} but no user account found")
            except Exception as e:
                # Don't fail task creation if WebSocket fails
                logger.error(f"Failed to emit task_assigned WebSocket event: {e}")
        
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
        project_id: Optional[int] = None,
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
        if project_id is not None:
            query = query.filter(Task.project_id == project_id)

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
        db: Session, company_id: int, task_id: int, data: TaskUpdate, current_user_id: Optional[int] = None
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
        
        # Validate project (if changed)
        if data.project_id is not None:
            if data.project_id:
                project = db.query(Project).filter(
                    Project.id == data.project_id,
                    Project.company_id == company_id,
                    Project.is_active == True,
                ).first()
                if not project:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Project not found in company",
                    )
            # allow setting to None to unassign from project

        # Track old status for WebSocket event
        old_status = task.status.value if task.status else None
        
        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)
        
        # Sync to vector database after update
        try:
            sync_service = VectorSyncService()
            sync_service.sync_task(db, task.id)
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to vector store after update: {str(e)}")
            # Don't fail the main operation if vector sync fails
        
        # Emit WebSocket event if status changed
        new_status = task.status.value if task.status else None
        if old_status and new_status and old_status != new_status:
            try:
                from app.api.v1.services.websocket_service import websocket_service
                from app.api.v1.models.user_model import User
                from app.api.v1.utils.websocket_helper import emit_websocket_event_async
                
                # Get current user who made the update
                updater_name = "Admin"
                updater_user = None
                if current_user_id:
                    updater_user = db.query(User).filter(User.id == current_user_id).first()
                    if updater_user:
                        updater_name = updater_user.full_name
                        # If employee updated, notify admin
                        if updater_user.role.value == "employee":
                            # Employee updated task - notify admin
                            emit_websocket_event_async(
                                websocket_service.emit_task_status_updated(
                                    db=db,
                                    tenant_id=company_id,
                                    task_id=task.id,
                                    task_name=task.title,
                                    employee_name=updater_name,
                                    new_status=new_status,
                                    old_status=old_status,
                                    assigned_to_employee_id=task.assigned_to_employee_id,
                                    created_by_user_id=task.created_by_user_id
                                )
                            )
                        else:
                            # Admin updated task - notify assigned employee if exists
                            if task.assigned_to_employee_id:
                                assigned_user = db.query(User).filter(User.employee_id == task.assigned_to_employee_id).first()
                                if assigned_user:
                                    emit_websocket_event_async(
                                        websocket_service.emit_task_status_updated(
                                            db=db,
                                            tenant_id=company_id,
                                            task_id=task.id,
                                            task_name=task.title,
                                            employee_name=updater_name,
                                            new_status=new_status,
                                            old_status=old_status,
                                            assigned_to_employee_id=task.assigned_to_employee_id,
                                            created_by_user_id=task.created_by_user_id
                                        )
                                    )
                else:
                    # Fallback: notify admin
                    emit_websocket_event_async(
                        websocket_service.emit_task_status_updated(
                            db=db,
                            tenant_id=company_id,
                            task_id=task.id,
                            task_name=task.title,
                            employee_name=updater_name,
                            new_status=new_status,
                            old_status=old_status,
                            assigned_to_employee_id=task.assigned_to_employee_id,
                            created_by_user_id=task.created_by_user_id
                        )
                    )
            except Exception as e:
                # Don't fail task update if WebSocket fails
                logger.error(f"Failed to emit task_status_updated WebSocket event: {e}")
        
        # Emit WebSocket event if task was reassigned
        if data.assigned_to_employee_id is not None and data.assigned_to_employee_id != task.assigned_to_employee_id:
            if data.assigned_to_employee_id:  # Only if assigned (not unassigned)
                try:
                    from app.api.v1.services.websocket_service import websocket_service
                    from app.api.v1.models.user_model import User
                    from app.api.v1.utils.websocket_helper import emit_websocket_event_async
                    
                    # Get creator user info
                    creator_user = db.query(User).filter(User.id == task.created_by_user_id).first()
                    creator_name = creator_user.full_name if creator_user else "Admin"
                    
                    # Get user_id from employee_id
                    assigned_user = db.query(User).filter(
                        User.employee_id == data.assigned_to_employee_id,
                        User.company_id == company_id
                    ).first()
                    
                    if assigned_user:
                        emit_websocket_event_async(
                            websocket_service.emit_task_assigned(
                                db=db,
                                tenant_id=company_id,
                                task_id=task.id,
                                task_name=task.title,
                                assigned_to=assigned_user.id,  # Use user_id
                                assigned_by=task.created_by_user_id,
                                assigned_by_name=creator_name
                            )
                        )
                    else:
                        logger.info(f"Task {task.id} reassigned to employee {data.assigned_to_employee_id} but no user account found")
                except Exception as e:
                    # Don't fail task update if WebSocket fails
                    logger.error(f"Failed to emit task_assigned WebSocket event on reassignment: {e}")
        
        return task

    # ─── Hierarchy helpers ────────────────────────────────────────────

    @staticmethod
    def _next_position(db: Session, company_id: int, parent_task_id: Optional[int]) -> int:
        """Return the next available position under a given parent (or top-level)."""
        from sqlalchemy import func
        q = db.query(func.count(Task.id)).filter(Task.company_id == company_id)
        if parent_task_id is None:
            q = q.filter(Task.parent_task_id.is_(None))
        else:
            q = q.filter(Task.parent_task_id == parent_task_id)
        return q.scalar() or 0

    @staticmethod
    def create_subtask(
        db: Session,
        company_id: int,
        creator_user_id: int,
        parent_task_id: int,
        data: SubtaskCreate,
    ) -> Task:
        """Create a child task under an existing task."""
        # Validate parent exists and belongs to company
        parent = db.query(Task).filter(
            Task.id == parent_task_id,
            Task.company_id == company_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent task not found")

        # Validate assignee
        if data.assigned_to_employee_id:
            assignee = db.query(Employee).filter(
                Employee.id == data.assigned_to_employee_id,
                Employee.company_id == company_id,
                Employee.is_active == True,
            ).first()
            if not assignee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned employee not found in company")

        position = TaskService._next_position(db, company_id, parent_task_id)

        task = Task(
            company_id=company_id,
            title=data.title,
            description=data.description,
            priority=data.priority or TaskPriority.MEDIUM,
            status=TaskStatus.OPEN,
            due_date=data.due_date,
            assigned_to_employee_id=data.assigned_to_employee_id,
            project_id=data.project_id or parent.project_id,
            created_by_user_id=creator_user_id,
            parent_task_id=parent_task_id,
            position=position,
            branch=data.branch,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            sync_service = VectorSyncService()
            sync_service.sync_task(db, task.id)
        except Exception as e:
            logger.error(f"Failed to sync subtask {task.id} to vector store: {e}")

        return task

    @staticmethod
    def list_subtasks(db: Session, company_id: int, parent_task_id: int) -> List[Task]:
        """Return direct children of a task, ordered by position."""
        # Validate parent
        parent = db.query(Task).filter(
            Task.id == parent_task_id,
            Task.company_id == company_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent task not found")

        return (
            db.query(Task)
            .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
            .filter(Task.company_id == company_id, Task.parent_task_id == parent_task_id)
            .order_by(Task.position)
            .all()
        )

    @staticmethod
    def _load_subtask_tree(db: Session, company_id: int, task: Task) -> Task:
        """Recursively eager-load subtasks onto a task object (in-place)."""
        children = (
            db.query(Task)
            .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
            .filter(Task.company_id == company_id, Task.parent_task_id == task.id)
            .order_by(Task.position)
            .all()
        )
        for child in children:
            TaskService._load_subtask_tree(db, company_id, child)
        task.subtasks = children
        return task

    @staticmethod
    def _assign_task_numbers(tasks: List[Task], prefix: str = "") -> int:
        """
        Walk the subtask tree and attach a computed `task_number` attribute
        (e.g. "1", "1.2", "2.1.3") to each Task object.
        Returns total count of nodes visited (for summary stats).
        """
        total = 0
        for idx, task in enumerate(tasks):
            num = f"{idx + 1}" if not prefix else f"{prefix}.{idx + 1}"
            task.task_number = num  # type: ignore[attr-defined]
            total += 1
            if hasattr(task, "subtasks") and task.subtasks:
                total += TaskService._assign_task_numbers(task.subtasks, num)
        return total

    @staticmethod
    def get_task_tree(db: Session, company_id: int, task_id: int) -> Tuple[Task, int]:
        """
        Return the task with all nested subtasks loaded as a tree.
        Also returns the total count of all nodes in the tree (including root).
        """
        task = (
            db.query(Task)
            .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
            .filter(Task.id == task_id, Task.company_id == company_id)
            .first()
        )
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        TaskService._load_subtask_tree(db, company_id, task)
        task.task_number = "1"  # type: ignore[attr-defined]
        total = 1
        if task.subtasks:
            total += TaskService._assign_task_numbers(task.subtasks, "1")
        return task, total

    @staticmethod
    def list_tasks_as_tree(
        db: Session,
        company_id: int,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        assigned_to_employee_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> Tuple[List[Task], int]:
        """
        Return all top-level tasks (parent_task_id IS NULL) with full nested subtrees.
        Returns (root_tasks, total_node_count_across_all_trees).
        """
        query = (
            db.query(Task)
            .options(joinedload(Task.assigned_to_employee), joinedload(Task.project))
            .filter(Task.company_id == company_id, Task.parent_task_id.is_(None))
        )
        if status_filter:
            query = query.filter(Task.status == status_filter)
        if priority_filter:
            query = query.filter(Task.priority == priority_filter)
        if assigned_to_employee_id:
            query = query.filter(Task.assigned_to_employee_id == assigned_to_employee_id)
        if project_id:
            query = query.filter(Task.project_id == project_id)

        root_tasks = query.order_by(Task.position).all()
        for t in root_tasks:
            TaskService._load_subtask_tree(db, company_id, t)

        total = TaskService._assign_task_numbers(root_tasks)
        return root_tasks, total

    @staticmethod
    def close_task(db: Session, company_id: int, task_id: int) -> Task:
        task = TaskService.get_task_by_id(db, company_id, task_id)
        old_status = task.status.value if task.status else None
        task.status = TaskStatus.CLOSED
        db.commit()
        db.refresh(task)
        
        # Sync to vector database after status change
        try:
            sync_service = VectorSyncService()
            sync_service.sync_task(db, task.id)
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to vector store after close: {str(e)}")
            # Don't fail the main operation if vector sync fails
        
        # Emit WebSocket event for status change
        try:
            from app.api.v1.services.websocket_service import websocket_service
            from app.api.v1.models.user_model import User
            from app.api.v1.utils.websocket_helper import emit_websocket_event_async
            
            # Get current user who closed the task (we'll need to pass this from route)
            # For now, try to get from task creator or assigned employee
            updater_name = "Admin"
            if task.assigned_to_employee_id:
                assigned_employee = db.query(Employee).filter(Employee.id == task.assigned_to_employee_id).first()
                if assigned_employee:
                    updater_name = assigned_employee.full_name
            
            # Get assigned user_id for notification
            assigned_user_id = None
            if task.assigned_to_employee_id:
                assigned_user = db.query(User).filter(User.employee_id == task.assigned_to_employee_id).first()
                assigned_user_id = assigned_user.id if assigned_user else None
            
            emit_websocket_event_async(
                websocket_service.emit_task_status_updated(
                    db=db,
                    tenant_id=company_id,
                    task_id=task.id,
                    task_name=task.title,
                    employee_name=updater_name,
                    new_status="CLOSED",
                    old_status=old_status,
                    assigned_to_employee_id=task.assigned_to_employee_id,
                    created_by_user_id=task.created_by_user_id
                )
            )
        except Exception as e:
            # Don't fail task close if WebSocket fails
            logger.error(f"Failed to emit task_status_updated WebSocket event on close: {e}")
        
        return task

    @staticmethod
    def _descendant_task_ids(db: Session, company_id: int, task_id: int) -> List[int]:
        ids = [task_id]
        children = (
            db.query(Task.id)
            .filter(Task.company_id == company_id, Task.parent_task_id == task_id)
            .all()
        )
        for (child_id,) in children:
            ids.extend(TaskService._descendant_task_ids(db, company_id, child_id))
        return ids

    @staticmethod
    def delete_task(db: Session, company_id: int, task_id: int) -> None:
        task = TaskService.get_task_by_id(db, company_id, task_id)
        task_ids = TaskService._descendant_task_ids(db, company_id, task_id)

        db.delete(task)
        db.commit()

        try:
            sync_service = VectorSyncService()
            for descendant_id in task_ids:
                try:
                    sync_service.delete_content(db, company_id, "task", descendant_id)
                except Exception as e:
                    logger.error(
                        f"Failed to delete vector store entry for task {descendant_id}: {str(e)}"
                    )
        except Exception as e:
            logger.error(f"Failed to sync vector store after deleting task {task_id}: {str(e)}")


