from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta
import logging

from app.api.v1.repositories.workflow_repository import (
    WorkflowRepository, ProjectWorkflowRepository, TaskWorkflowRepository, SLARepository
)
from app.api.v1.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowEdge, ProjectWorkflow,
    NodeType, SLAStatus
)
from app.api.v1.models.task_model import Task
from app.api.v1.models.project_model import Project
from app.api.v1.schemas.workflow_schema import WorkflowCreate, WorkflowUpdate

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow template operations"""
    
    @staticmethod
    def create_workflow(
        db: Session,
        company_id: int,
        data: WorkflowCreate
    ) -> Workflow:
        """Create workflow template"""
        # Validate nodes
        start_nodes = [n for n in data.nodes if n.node_type == "start"]
        if not start_nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow must have at least one start node"
            )
        
        # Check node_key uniqueness
        node_keys = [n.node_key for n in data.nodes]
        if len(node_keys) != len(set(node_keys)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node keys must be unique within workflow"
            )
        
        # Validate edges reference valid nodes
        node_key_set = set(node_keys)
        for edge in data.edges:
            if edge.source_node_key not in node_key_set:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Edge references non-existent source node: {edge.source_node_key}"
                )
            if edge.target_node_key not in node_key_set:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Edge references non-existent target node: {edge.target_node_key}"
                )
        
        # Prepare nodes and edges data
        nodes_data = [node.model_dump() for node in data.nodes]
        edges_data = [edge.model_dump() for edge in data.edges]
        
        workflow = WorkflowRepository.create_workflow(
            db=db,
            company_id=company_id,
            name=data.name,
            nodes_data=nodes_data,
            edges_data=edges_data
        )
        
        logger.info(f"Created workflow {workflow.id} ({workflow.name}) for company {company_id}")
        return workflow
    
    @staticmethod
    def get_workflow(
        db: Session,
        workflow_id: UUID,
        company_id: int
    ) -> Workflow:
        """Get workflow with nodes and edges"""
        workflow = WorkflowRepository.get_workflow_with_nodes_edges(
            db=db,
            workflow_id=workflow_id,
            company_id=company_id
        )
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        return workflow
    
    @staticmethod
    def list_workflows(
        db: Session,
        company_id: int,
        include_inactive: bool = False
    ) -> List[Workflow]:
        """List workflows"""
        return WorkflowRepository.list_workflows(
            db=db,
            company_id=company_id,
            include_inactive=include_inactive
        )
    
    @staticmethod
    def update_workflow(
        db: Session,
        workflow_id: UUID,
        company_id: int,
        data: WorkflowUpdate
    ) -> Workflow:
        """Update workflow (creates new version)"""
        workflow = WorkflowRepository.get_workflow_by_id(db, workflow_id, company_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Validate if nodes/edges are provided
        if data.nodes is not None:
            start_nodes = [n for n in data.nodes if n.node_type == "start"]
            if not start_nodes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workflow must have at least one start node"
                )
            
            # Check node_key uniqueness
            node_keys = [n.node_key for n in data.nodes]
            if len(node_keys) != len(set(node_keys)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Node keys must be unique within workflow"
                )
        
        # Prepare update data
        nodes_data = [node.model_dump() for node in data.nodes] if data.nodes else None
        edges_data = [edge.model_dump() for edge in data.edges] if data.edges else None
        
        updated_workflow = WorkflowRepository.update_workflow(
            db=db,
            workflow_id=workflow_id,
            company_id=company_id,
            name=data.name,
            nodes_data=nodes_data,
            edges_data=edges_data
        )
        
        logger.info(f"Updated workflow {workflow_id} - new version: {updated_workflow.version}")
        return updated_workflow
    
    @staticmethod
    def delete_workflow(
        db: Session,
        workflow_id: UUID,
        company_id: int
    ) -> bool:
        """Soft delete workflow"""
        success = WorkflowRepository.delete_workflow(db, workflow_id, company_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        logger.info(f"Soft-deleted workflow {workflow_id}")
        return True


class ProjectWorkflowService:
    """Service for project workflow operations"""
    
    @staticmethod
    def assign_workflow_to_project(
        db: Session,
        project_id: int,
        workflow_template_id: UUID,
        company_id: int
    ) -> ProjectWorkflow:
        """Assign workflow template to project"""
        # Verify project exists and belongs to company
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.company_id == company_id
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Verify workflow exists and belongs to company
        workflow = WorkflowRepository.get_workflow_by_id(db, workflow_template_id, company_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow template not found"
            )
        
        if not workflow.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign inactive workflow template"
            )
        
        # Check if project already has a workflow
        existing = ProjectWorkflowRepository.get_project_workflow(db, project_id, company_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project already has a workflow assigned"
            )
        
        # Create project workflow instance
        project_workflow = ProjectWorkflowRepository.create_project_workflow(
            db=db,
            project_id=project_id,
            workflow_template_id=workflow_template_id
        )
        
        logger.info(f"Assigned workflow {workflow_template_id} to project {project_id}")
        return project_workflow
    
    @staticmethod
    def configure_users(
        db: Session,
        project_id: int,
        company_id: int,
        user_assignments: List[Dict[str, Any]]
    ) -> List[ProjectWorkflow]:
        """Configure users for project workflow roles"""
        # Get project workflow
        project_workflow = ProjectWorkflowRepository.get_project_workflow(db, project_id, company_id)
        if not project_workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project workflow not found. Please assign a workflow first."
            )
        
        # Validate users belong to company
        from app.api.v1.models.user_model import User
        user_ids = [ua["user_id"] for ua in user_assignments]
        users = db.query(User).filter(
            User.id.in_(user_ids),
            User.company_id == company_id
        ).all()
        if len(users) != len(user_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more users not found in company"
            )
        
        # Assign users to roles
        assignments = ProjectWorkflowRepository.assign_users_to_roles(
            db=db,
            project_workflow_id=project_workflow.id,
            user_assignments=user_assignments
        )
        
        logger.info(f"Configured {len(assignments)} user assignments for project workflow {project_workflow.id}")
        return assignments

