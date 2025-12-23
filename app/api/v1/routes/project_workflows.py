from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user, require_admin_role
from app.api.v1.models.user_model import User
from app.api.v1.schemas.workflow_schema import (
    ProjectWorkflowAssign,
    ProjectWorkflowConfigureUsers,
    ProjectWorkflowResponse,
    ProjectWorkflowUserResponse
)
from app.api.v1.services.workflow_service import ProjectWorkflowService
from app.api.v1.repositories.workflow_repository import ProjectWorkflowRepository
from typing import List

router = APIRouter(prefix="/projects", tags=["Project Workflows"])


@router.post("/{project_id}/assign-workflow", response_model=ProjectWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def assign_workflow_to_project(
    project_id: int,
    assignment_data: ProjectWorkflowAssign,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Assign workflow template to project.
    Creates a project workflow instance.
    Only admins can assign workflows.
    """
    project_workflow = ProjectWorkflowService.assign_workflow_to_project(
        db=db,
        project_id=project_id,
        workflow_template_id=assignment_data.workflow_template_id,
        company_id=current_user.company_id
    )
    
    # Load relationships
    db.refresh(project_workflow)
    if project_workflow.workflow_template:
        db.refresh(project_workflow.workflow_template)
    
    return ProjectWorkflowResponse.model_validate(project_workflow)


@router.post("/{project_id}/configure-users", response_model=List[ProjectWorkflowUserResponse], status_code=status.HTTP_201_CREATED)
async def configure_project_workflow_users(
    project_id: int,
    config_data: ProjectWorkflowConfigureUsers,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_database_session)
):
    """
    Configure users for project workflow roles.
    Assigns users to specific roles (e.g., Developer, Tester, Manager).
    Only admins can configure users.
    """
    user_assignments = [ua.model_dump() for ua in config_data.user_assignments]
    
    assignments = ProjectWorkflowService.configure_users(
        db=db,
        project_id=project_id,
        company_id=current_user.company_id,
        user_assignments=user_assignments
    )
    
    # Load user information
    from app.api.v1.models.user_model import User
    result = []
    for assignment in assignments:
        db.refresh(assignment)
        if assignment.user:
            db.refresh(assignment.user)
        assignment_dict = ProjectWorkflowUserResponse.model_validate(assignment).model_dump()
        if assignment.user:
            assignment_dict["user"] = {
                "id": assignment.user.id,
                "username": assignment.user.username,
                "full_name": assignment.user.full_name,
                "email": assignment.user.email
            }
        result.append(assignment_dict)
    
    return result


@router.get("/{project_id}/workflow", response_model=ProjectWorkflowResponse)
async def get_project_workflow(
    project_id: int,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get project workflow assignment.
    """
    project_workflow = ProjectWorkflowRepository.get_project_workflow(
        db=db,
        project_id=project_id,
        company_id=current_user.company_id
    )
    
    if not project_workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project workflow not found"
        )
    
    # Load relationships
    db.refresh(project_workflow)
    if project_workflow.workflow_template:
        db.refresh(project_workflow.workflow_template)
    project_workflow.users
    
    return ProjectWorkflowResponse.model_validate(project_workflow)

