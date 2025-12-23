from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.schemas.workflow_schema import (
    TaskCreateWithWorkflow,
    TaskTransitionRequest,
    TaskWorkflowResponse,
    TaskStateHistoryResponse
)
from app.api.v1.services.task_workflow_service import TaskWorkflowService
from app.api.v1.repositories.workflow_repository import TaskWorkflowRepository
from app.api.v1.models.task_model import Task
from app.api.v1.models.workflow_model import WorkflowNode

router = APIRouter(prefix="/projects", tags=["Task Workflows"])


@router.post("/{project_id}/tasks", response_model=TaskWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_task_with_workflow(
    project_id: int,
    task_data: TaskCreateWithWorkflow,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create task and initialize workflow at start node.
    Task will be placed at the workflow's start node and SLA tracking will begin.
    """
    task = TaskWorkflowService.create_task_with_workflow(
        db=db,
        project_id=project_id,
        company_id=current_user.company_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority or "medium",
        due_date=task_data.due_date,
        created_by_user_id=current_user.id
    )
    
    # Load workflow information
    db.refresh(task)
    if task.current_node:
        db.refresh(task.current_node)
    task.state_history
    
    # Build response
    task_dict = TaskWorkflowResponse.model_validate(task).model_dump()
    if task.current_node:
        task_dict["current_node_key"] = task.current_node.node_key
        task_dict["current_node_type"] = task.current_node.node_type.value
        task_dict["current_role"] = task.current_node.role
    
    # Enhance state history with node keys
    for history in task_dict["state_history"]:
        if history.get("from_node_id"):
            from_node = db.query(Task.current_node).filter(
                Task.current_node_id == history["from_node_id"]
            ).first()
            if from_node:
                history["from_node_key"] = from_node.node_key
        if history.get("to_node_id"):
            to_node = db.query(Task.current_node).filter(
                Task.current_node_id == history["to_node_id"]
            ).first()
            if to_node:
                history["to_node_key"] = to_node.node_key
    
    return task_dict


@router.get("/tasks/{task_id}", response_model=TaskWorkflowResponse)
async def get_task_with_workflow(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get task details with current workflow node and state history.
    """
    task = TaskWorkflowRepository.get_task_with_workflow(
        db=db,
        task_id=task_id,
        company_id=current_user.company_id
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Load workflow information
    db.refresh(task)
    if task.current_node:
        db.refresh(task.current_node)
    task.state_history
    
    # Build response
    task_dict = TaskWorkflowResponse.model_validate(task).model_dump()
    if task.current_node:
        task_dict["current_node_key"] = task.current_node.node_key
        task_dict["current_node_type"] = task.current_node.node_type.value
        task_dict["current_role"] = task.current_node.role
    
    # Enhance state history
    from app.api.v1.models.workflow_model import WorkflowNode
    for history_item in task.state_history:
        history_dict = TaskStateHistoryResponse.model_validate(history_item).model_dump()
        if history_item.from_node_id:
            from_node = db.query(WorkflowNode).filter(
                WorkflowNode.id == history_item.from_node_id
            ).first()
            if from_node:
                history_dict["from_node_key"] = from_node.node_key
        if history_item.to_node_id:
            to_node = db.query(WorkflowNode).filter(
                WorkflowNode.id == history_item.to_node_id
            ).first()
            if to_node:
                history_dict["to_node_key"] = to_node.node_key
        if history_item.performed_by:
            from app.api.v1.models.user_model import User
            performer = db.query(User).filter(User.id == history_item.performed_by).first()
            if performer:
                history_dict["performer_name"] = performer.full_name
        task_dict["state_history"].append(history_dict)
    
    return task_dict


@router.post("/tasks/{task_id}/transition", response_model=TaskWorkflowResponse)
async def transition_task(
    task_id: int,
    transition_data: TaskTransitionRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Move task to next node based on action and edge condition.
    Validates edge conditions and updates task state.
    """
    task = TaskWorkflowService.transition_task(
        db=db,
        task_id=task_id,
        company_id=current_user.company_id,
        action=transition_data.action,
        condition_data=transition_data.condition_data,
        performed_by_user_id=current_user.id
    )
    
    # Load workflow information
    db.refresh(task)
    if task.current_node:
        db.refresh(task.current_node)
    task.state_history
    
    # Build response
    task_dict = TaskWorkflowResponse.model_validate(task).model_dump()
    if task.current_node:
        task_dict["current_node_key"] = task.current_node.node_key
        task_dict["current_node_type"] = task.current_node.node_type.value
        task_dict["current_role"] = task.current_node.role
    
    return task_dict

