from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta
import logging

from app.api.v1.repositories.workflow_repository import (
    WorkflowRepository, ProjectWorkflowRepository, TaskWorkflowRepository, SLARepository
)
from app.api.v1.models.workflow_model import (
    WorkflowNode, WorkflowEdge, ProjectWorkflow, TaskStateHistory,
    NodeType, SLAStatus
)
from app.api.v1.models.task_model import Task, TaskStatus
from app.api.v1.models.project_model import Project

logger = logging.getLogger(__name__)


class TaskWorkflowService:
    """Service for task workflow execution"""
    
    @staticmethod
    def create_task_with_workflow(
        db: Session,
        project_id: int,
        company_id: int,
        title: str,
        description: Optional[str],
        priority: str,
        due_date: Optional[datetime],
        created_by_user_id: int
    ) -> Task:
        """Create task and initialize workflow at start node"""
        # Verify project exists
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.company_id == company_id
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get project workflow
        project_workflow = ProjectWorkflowRepository.get_project_workflow(db, project_id, company_id)
        if not project_workflow:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a workflow assigned. Please assign a workflow first."
            )
        
        # Get workflow template
        workflow = WorkflowRepository.get_workflow_with_nodes_edges(
            db=db,
            workflow_id=project_workflow.workflow_template_id,
            company_id=company_id
        )
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow template not found"
            )
        
        # Find start node
        start_node = WorkflowRepository.get_start_node(db, workflow.id)
        if not start_node:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow does not have a start node"
            )
        
        # Create task
        task = Task(
            company_id=company_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            project_id=project_id,
            project_workflow_id=project_workflow.id,
            current_node_id=start_node.id,
            status=TaskStatus.OPEN,
            created_by_user_id=created_by_user_id
        )
        db.add(task)
        db.flush()
        
        # Create initial state history
        TaskWorkflowRepository.create_state_history(
            db=db,
            task_id=task.id,
            from_node_id=None,
            to_node_id=start_node.id,
            action="created",
            performed_by=created_by_user_id
        )
        
        # Initialize SLA tracking for start node
        TaskWorkflowService._initialize_sla_for_node(
            db=db,
            task_id=task.id,
            workflow_node_id=start_node.id
        )
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Created task {task.id} with workflow initialized at node {start_node.node_key}")
        return task
    
    @staticmethod
    def transition_task(
        db: Session,
        task_id: int,
        company_id: int,
        action: Optional[str],
        condition_data: Optional[Dict[str, Any]],
        performed_by_user_id: int
    ) -> Task:
        """Transition task to next node based on action and edge condition"""
        # Get task with workflow
        task = TaskWorkflowRepository.get_task_with_workflow(db, task_id, company_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if not task.project_workflow_id or not task.current_node_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not have workflow initialized"
            )
        
        # Get project workflow and workflow template
        project_workflow = db.query(ProjectWorkflow).filter(
            ProjectWorkflow.id == task.project_workflow_id
        ).first()
        if not project_workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project workflow not found"
            )
        
        workflow = WorkflowRepository.get_workflow_with_nodes_edges(
            db=db,
            workflow_id=project_workflow.workflow_template_id,
            company_id=company_id
        )
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow template not found"
            )
        
        # Get current node
        current_node = db.query(WorkflowNode).filter(
            WorkflowNode.id == task.current_node_id
        ).first()
        if not current_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Current workflow node not found"
            )
        
        # Check if current node is end node
        if current_node.node_type == NodeType.END:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task has reached end node. No further transitions allowed."
            )
        
        # Get available edges from current node
        edges = TaskWorkflowRepository.get_edges_from_node(
            db=db,
            workflow_id=workflow.id,
            node_id=current_node.id
        )
        
        if not edges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transitions available from current node"
            )
        
        # Find matching edge based on condition
        target_edge = None
        for edge in edges:
            if TaskWorkflowService._evaluate_edge_condition(edge, action, condition_data):
                target_edge = edge
                break
        
        if not target_edge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching transition found for given action/condition"
            )
        
        # Get target node
        target_node = db.query(WorkflowNode).filter(
            WorkflowNode.id == target_edge.target_node_id
        ).first()
        if not target_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target workflow node not found"
            )
        
        # Update task current node
        old_node_id = task.current_node_id
        task.current_node_id = target_node.id
        
        # Update task status based on node type
        if target_node.node_type == NodeType.END:
            task.status = TaskStatus.CLOSED
        elif target_node.node_type == NodeType.ASSIGN or target_node.node_type == NodeType.ACTION:
            task.status = TaskStatus.IN_PROGRESS
        
        # Assign task to user based on role if assign node
        if target_node.node_type == NodeType.ASSIGN and target_node.role:
            assigned_user = ProjectWorkflowRepository.get_user_by_role(
                db=db,
                project_workflow_id=project_workflow.id,
                role=target_node.role
            )
            if assigned_user:
                # Get employee for user
                from app.api.v1.models.employee_model import Employee
                employee = db.query(Employee).filter(
                    Employee.user_id == assigned_user.user_id
                ).first()
                if employee:
                    task.assigned_to_employee_id = employee.id
        
        task.updated_at = datetime.utcnow()
        db.flush()
        
        # Create state history
        TaskWorkflowRepository.create_state_history(
            db=db,
            task_id=task.id,
            from_node_id=old_node_id,
            to_node_id=target_node.id,
            action=action,
            performed_by=performed_by_user_id
        )
        
        # Update SLA tracking for old node (mark as met if completed)
        TaskWorkflowService._update_sla_for_node_completion(
            db=db,
            task_id=task.id,
            workflow_node_id=old_node_id
        )
        
        # Initialize SLA tracking for new node
        TaskWorkflowService._initialize_sla_for_node(
            db=db,
            task_id=task.id,
            workflow_node_id=target_node.id
        )
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} transitioned from {current_node.node_key} to {target_node.node_key}")
        return task
    
    @staticmethod
    def _evaluate_edge_condition(
        edge: WorkflowEdge,
        action: Optional[str],
        condition_data: Optional[Dict[str, Any]]
    ) -> bool:
        """Evaluate if edge condition matches action/condition_data"""
        if not edge.condition:
            # No condition means always valid
            return True
        
        condition = edge.condition
        
        # Check action match
        if "action" in condition:
            if condition["action"] != action:
                return False
        
        # Check other condition fields
        if condition_data:
            for key, value in condition.items():
                if key != "action" and key in condition_data:
                    if condition_data[key] != value:
                        return False
        
        return True
    
    @staticmethod
    def _initialize_sla_for_node(
        db: Session,
        task_id: int,
        workflow_node_id: UUID
    ):
        """Initialize SLA tracking for a workflow node"""
        # Get SLA definition for node
        sla_def = SLARepository.get_sla_for_node(db, workflow_node_id)
        if not sla_def:
            return
        
        # Calculate deadlines
        now = datetime.utcnow()
        response_deadline = None
        resolution_deadline = None
        
        if sla_def.response_time_hours:
            response_deadline = now + timedelta(hours=sla_def.response_time_hours)
        
        if sla_def.resolution_time_hours:
            resolution_deadline = now + timedelta(hours=sla_def.resolution_time_hours)
        
        # Create SLA tracking
        SLARepository.create_sla_tracking(
            db=db,
            task_id=task_id,
            workflow_node_id=workflow_node_id,
            response_deadline=response_deadline,
            resolution_deadline=resolution_deadline
        )
    
    @staticmethod
    def _update_sla_for_node_completion(
        db: Session,
        task_id: int,
        workflow_node_id: UUID
    ):
        """Update SLA status when node is completed"""
        # Get current SLA tracking for this node
        sla_trackings = SLARepository.get_task_sla_tracking(
            db=db,
            task_id=task_id,
            workflow_node_id=workflow_node_id
        )
        
        for tracking in sla_trackings:
            if tracking.sla_status == SLAStatus.PENDING or tracking.sla_status == SLAStatus.IN_PROGRESS:
                # Check if deadlines were met
                now = datetime.utcnow()
                breached = False
                
                if tracking.resolution_deadline and now > tracking.resolution_deadline:
                    breached = True
                elif tracking.response_deadline and now > tracking.response_deadline:
                    # Response deadline breached but resolution not yet
                    pass
                
                if breached:
                    SLARepository.update_sla_status(
                        db=db,
                        sla_tracking_id=tracking.id,
                        status=SLAStatus.BREACHED,
                        breached_at=now
                    )
                else:
                    SLARepository.update_sla_status(
                        db=db,
                        sla_tracking_id=tracking.id,
                        status=SLAStatus.MET
                    )

