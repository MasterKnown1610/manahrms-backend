from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.models.user_model import User
from app.api.v1.schemas.workflow_schema import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListItem
)
from app.api.v1.schemas.user_schema import MessageResponse
from app.api.v1.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Create a new workflow template with nodes and edges.
    Only admins can create workflows.
    """
    workflow = WorkflowService.create_workflow(
        db=db,
        company_id=current_user.company_id,
        data=workflow_data
    )
    
    # Load nodes and edges for response
    db.refresh(workflow)
    workflow.nodes
    workflow.edges
    
    return WorkflowResponse.model_validate(workflow)


@router.get("", response_model=List[WorkflowListItem])
async def list_workflows(
    include_inactive: bool = Query(False, description="Include inactive workflows"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    List all workflow templates for the company.
    """
    workflows = WorkflowService.list_workflows(
        db=db,
        company_id=current_user.company_id,
        include_inactive=include_inactive
    )
    
    return [WorkflowListItem.model_validate(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get workflow template with nodes and edges by ID.
    """
    workflow = WorkflowService.get_workflow(
        db=db,
        workflow_id=workflow_id,
        company_id=current_user.company_id
    )
    
    # Enhance response with node keys for edges
    workflow_dict = WorkflowResponse.model_validate(workflow).model_dump()
    
    # Add node keys to edges
    node_id_to_key = {str(node.id): node.node_key for node in workflow.nodes}
    for edge in workflow_dict["edges"]:
        edge["source_node_key"] = node_id_to_key.get(str(edge["source_node_id"]))
        edge["target_node_key"] = node_id_to_key.get(str(edge["target_node_id"]))
    
    return workflow_dict


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_data: WorkflowUpdate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Update workflow template (creates new version).
    Only admins can update workflows.
    """
    workflow = WorkflowService.update_workflow(
        db=db,
        workflow_id=workflow_id,
        company_id=current_user.company_id,
        data=workflow_data
    )
    
    # Load nodes and edges for response
    db.refresh(workflow)
    workflow.nodes
    workflow.edges
    
    # Enhance response with node keys for edges
    workflow_dict = WorkflowResponse.model_validate(workflow).model_dump()
    node_id_to_key = {str(node.id): node.node_key for node in workflow.nodes}
    for edge in workflow_dict["edges"]:
        edge["source_node_key"] = node_id_to_key.get(str(edge["source_node_id"]))
        edge["target_node_key"] = node_id_to_key.get(str(edge["target_node_id"]))
    
    return workflow_dict


@router.delete("/{workflow_id}", response_model=MessageResponse)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Soft delete workflow template.
    Only admins can delete workflows.
    """
    WorkflowService.delete_workflow(
        db=db,
        workflow_id=workflow_id,
        company_id=current_user.company_id
    )
    
    return MessageResponse(message="Workflow deleted successfully")

