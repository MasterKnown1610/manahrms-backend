from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.schemas.workflow_schema import TaskSLAResponse
from app.api.v1.services.sla_service import SLAService
from app.api.v1.models.workflow_model import WorkflowNode

router = APIRouter(prefix="/tasks", tags=["SLA"])


@router.get("/{task_id}/sla", response_model=TaskSLAResponse)
async def get_task_sla(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get SLA status for a task.
    Returns current SLA tracking and all historical SLA records.
    """
    sla_data = SLAService.get_task_sla(
        db=db,
        task_id=task_id,
        company_id=current_user.company_id
    )
    
    # Enhance with node keys
    from app.api.v1.models.workflow_model import WorkflowNode
    if sla_data["current_sla"]:
        node = db.query(WorkflowNode).filter(
            WorkflowNode.id == sla_data["current_sla"].workflow_node_id
        ).first()
        if node:
            sla_data["current_sla"].workflow_node_key = node.node_key
    
    for tracking in sla_data["all_sla_tracking"]:
        node = db.query(WorkflowNode).filter(
            WorkflowNode.id == tracking.workflow_node_id
        ).first()
        if node:
            tracking.workflow_node_key = node.node_key
    
    return TaskSLAResponse(**sla_data)


@router.post("/{task_id}/sla/check", response_model=dict)
async def check_task_sla_breach(
    task_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Check and update SLA breach status for a task.
    Compares current time against deadlines and marks SLA as breached if exceeded.
    """
    result = SLAService.check_and_update_sla_breach(
        db=db,
        task_id=task_id,
        company_id=current_user.company_id
    )
    
    return result

