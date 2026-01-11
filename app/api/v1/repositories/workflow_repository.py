from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from datetime import datetime

from app.api.v1.models.workflow_model import (
    Workflow, WorkflowNode, WorkflowEdge, ProjectWorkflow,
    ProjectWorkflowUser, TaskStateHistory, SLADefinition, TaskSLATracking,
    NodeType, SLAStatus
)
from app.api.v1.models.task_model import Task
from app.api.v1.models.project_model import Project


class WorkflowRepository:
    """Repository for workflow template operations"""
    
    @staticmethod
    def create_workflow(
        db: Session,
        company_id: int,
        name: str,
        nodes_data: List[dict],
        edges_data: List[dict]
    ) -> Workflow:
        """Create workflow with nodes and edges"""
        workflow = Workflow(
            company_id=company_id,
            name=name,
            version=1,
            is_active=True
        )
        db.add(workflow)
        db.flush()
        
        # Create nodes
        node_key_map = {}  # Map node_key to node_id
        for node_data in nodes_data:
            node = WorkflowNode(
                workflow_id=workflow.id,
                node_key=node_data["node_key"],
                node_type=NodeType(node_data["node_type"]),
                role=node_data.get("role"),
                node_metadata=node_data.get("metadata"),
                position_x=node_data.get("position_x", 0),
                position_y=node_data.get("position_y", 0)
            )
            db.add(node)
            db.flush()
            node_key_map[node_data["node_key"]] = node.id
        
        # Create edges
        for edge_data in edges_data:
            source_id = node_key_map.get(edge_data["source_node_key"])
            target_id = node_key_map.get(edge_data["target_node_key"])
            if source_id and target_id:
                edge = WorkflowEdge(
                    workflow_id=workflow.id,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    condition=edge_data.get("condition")
                )
                db.add(edge)
        
        db.commit()
        db.refresh(workflow)
        return workflow
    
    @staticmethod
    def get_workflow_by_id(db: Session, workflow_id: UUID, company_id: int) -> Optional[Workflow]:
        """Get workflow by ID with company check"""
        return db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.company_id == company_id
        ).first()
    
    @staticmethod
    def get_workflow_with_nodes_edges(
        db: Session,
        workflow_id: UUID,
        company_id: int
    ) -> Optional[Workflow]:
        """Get workflow with nodes and edges"""
        workflow = WorkflowRepository.get_workflow_by_id(db, workflow_id, company_id)
        if workflow:
            # Eager load nodes and edges
            workflow.nodes
            workflow.edges
        return workflow
    
    @staticmethod
    def list_workflows(db: Session, company_id: int, include_inactive: bool = False) -> List[Workflow]:
        """List workflows for company"""
        query = db.query(Workflow).filter(Workflow.company_id == company_id)
        if not include_inactive:
            query = query.filter(Workflow.is_active == True)
        return query.order_by(Workflow.created_at.desc()).all()
    
    @staticmethod
    def update_workflow(
        db: Session,
        workflow_id: UUID,
        company_id: int,
        name: Optional[str] = None,
        nodes_data: Optional[List[dict]] = None,
        edges_data: Optional[List[dict]] = None
    ) -> Optional[Workflow]:
        """Update workflow (creates new version)"""
        workflow = WorkflowRepository.get_workflow_by_id(db, workflow_id, company_id)
        if not workflow:
            return None
        
        if name:
            workflow.name = name
        
        # If nodes/edges are updated, increment version and recreate them
        if nodes_data is not None or edges_data is not None:
            # Delete old nodes and edges
            db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow_id).delete()
            db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).delete()
            
            # Create new nodes
            node_key_map = {}
            nodes_data = nodes_data or []
            for node_data in nodes_data:
                node = WorkflowNode(
                    workflow_id=workflow.id,
                    node_key=node_data["node_key"],
                    node_type=NodeType(node_data["node_type"]),
                    role=node_data.get("role"),
                    metadata=node_data.get("metadata"),
                    position_x=node_data.get("position_x", 0),
                    position_y=node_data.get("position_y", 0)
                )
                db.add(node)
                db.flush()
                node_key_map[node_data["node_key"]] = node.id
            
            # Create new edges
            edges_data = edges_data or []
            for edge_data in edges_data:
                source_id = node_key_map.get(edge_data["source_node_key"])
                target_id = node_key_map.get(edge_data["target_node_key"])
                if source_id and target_id:
                    edge = WorkflowEdge(
                        workflow_id=workflow.id,
                        source_node_id=source_id,
                        target_node_id=target_id,
                        condition=edge_data.get("condition")
                    )
                    db.add(edge)
            
            workflow.version += 1
        
        workflow.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(workflow)
        return workflow
    
    @staticmethod
    def delete_workflow(db: Session, workflow_id: UUID, company_id: int) -> bool:
        """Soft delete workflow"""
        workflow = WorkflowRepository.get_workflow_by_id(db, workflow_id, company_id)
        if not workflow:
            return False
        workflow.is_active = False
        workflow.updated_at = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def get_start_node(db: Session, workflow_id: UUID) -> Optional[WorkflowNode]:
        """Get start node for workflow"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.node_type == NodeType.START
        ).first()
    
    @staticmethod
    def get_node_by_key(db: Session, workflow_id: UUID, node_key: str) -> Optional[WorkflowNode]:
        """Get node by key within workflow"""
        return db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.node_key == node_key
        ).first()


class ProjectWorkflowRepository:
    """Repository for project workflow operations"""
    
    @staticmethod
    def create_project_workflow(
        db: Session,
        project_id: int,
        workflow_template_id: UUID
    ) -> ProjectWorkflow:
        """Create project workflow instance"""
        project_workflow = ProjectWorkflow(
            project_id=project_id,
            workflow_template_id=workflow_template_id
        )
        db.add(project_workflow)
        db.commit()
        db.refresh(project_workflow)
        return project_workflow
    
    @staticmethod
    def get_project_workflow(
        db: Session,
        project_id: int,
        company_id: int
    ) -> Optional[ProjectWorkflow]:
        """Get project workflow for project"""
        return db.query(ProjectWorkflow).join(Project).filter(
            ProjectWorkflow.project_id == project_id,
            Project.company_id == company_id
        ).first()
    
    @staticmethod
    def assign_users_to_roles(
        db: Session,
        project_workflow_id: UUID,
        user_assignments: List[dict]
    ) -> List[ProjectWorkflowUser]:
        """Assign users to roles in project workflow"""
        # Delete existing assignments
        db.query(ProjectWorkflowUser).filter(
            ProjectWorkflowUser.project_workflow_id == project_workflow_id
        ).delete()
        
        # Create new assignments
        assignments = []
        for assignment_data in user_assignments:
            assignment = ProjectWorkflowUser(
                project_workflow_id=project_workflow_id,
                role=assignment_data["role"],
                user_id=assignment_data["user_id"]
            )
            db.add(assignment)
            assignments.append(assignment)
        
        db.commit()
        for assignment in assignments:
            db.refresh(assignment)
        return assignments
    
    @staticmethod
    def get_user_by_role(
        db: Session,
        project_workflow_id: UUID,
        role: str
    ) -> Optional[ProjectWorkflowUser]:
        """Get user assigned to specific role"""
        return db.query(ProjectWorkflowUser).filter(
            ProjectWorkflowUser.project_workflow_id == project_workflow_id,
            ProjectWorkflowUser.role == role
        ).first()


class TaskWorkflowRepository:
    """Repository for task workflow operations"""
    
    @staticmethod
    def get_task_with_workflow(db: Session, task_id: int, company_id: int) -> Optional[Task]:
        """Get task with workflow information"""
        return db.query(Task).filter(
            Task.id == task_id,
            Task.company_id == company_id
        ).first()
    
    @staticmethod
    def get_edges_from_node(
        db: Session,
        workflow_id: UUID,
        node_id: UUID
    ) -> List[WorkflowEdge]:
        """Get all edges from a node"""
        return db.query(WorkflowEdge).filter(
            WorkflowEdge.workflow_id == workflow_id,
            WorkflowEdge.source_node_id == node_id
        ).all()
    
    @staticmethod
    def create_state_history(
        db: Session,
        task_id: int,
        from_node_id: Optional[UUID],
        to_node_id: UUID,
        action: Optional[str],
        performed_by: Optional[int]
    ) -> TaskStateHistory:
        """Create task state history record"""
        history = TaskStateHistory(
            task_id=task_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            action=action,
            performed_by=performed_by
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    @staticmethod
    def get_task_state_history(
        db: Session,
        task_id: int
    ) -> List[TaskStateHistory]:
        """Get task state history"""
        return db.query(TaskStateHistory).filter(
            TaskStateHistory.task_id == task_id
        ).order_by(TaskStateHistory.created_at.asc()).all()


class SLARepository:
    """Repository for SLA operations"""
    
    @staticmethod
    def create_sla_definition(
        db: Session,
        workflow_node_id: UUID,
        response_time_hours: Optional[int],
        resolution_time_hours: Optional[int],
        escalation_role: Optional[str]
    ) -> SLADefinition:
        """Create SLA definition"""
        sla = SLADefinition(
            workflow_node_id=workflow_node_id,
            response_time_hours=response_time_hours,
            resolution_time_hours=resolution_time_hours,
            escalation_role=escalation_role
        )
        db.add(sla)
        db.commit()
        db.refresh(sla)
        return sla
    
    @staticmethod
    def get_sla_for_node(db: Session, workflow_node_id: UUID) -> Optional[SLADefinition]:
        """Get SLA definition for node"""
        return db.query(SLADefinition).filter(
            SLADefinition.workflow_node_id == workflow_node_id
        ).first()
    
    @staticmethod
    def create_sla_tracking(
        db: Session,
        task_id: int,
        workflow_node_id: UUID,
        response_deadline: Optional[datetime],
        resolution_deadline: Optional[datetime]
    ) -> TaskSLATracking:
        """Create SLA tracking record"""
        tracking = TaskSLATracking(
            task_id=task_id,
            workflow_node_id=workflow_node_id,
            sla_status=SLAStatus.PENDING,
            started_at=datetime.utcnow(),
            response_deadline=response_deadline,
            resolution_deadline=resolution_deadline
        )
        db.add(tracking)
        db.commit()
        db.refresh(tracking)
        return tracking
    
    @staticmethod
    def get_task_sla_tracking(
        db: Session,
        task_id: int,
        workflow_node_id: Optional[UUID] = None
    ) -> List[TaskSLATracking]:
        """Get SLA tracking for task"""
        query = db.query(TaskSLATracking).filter(
            TaskSLATracking.task_id == task_id
        )
        if workflow_node_id:
            query = query.filter(TaskSLATracking.workflow_node_id == workflow_node_id)
        return query.order_by(TaskSLATracking.started_at.desc()).all()
    
    @staticmethod
    def update_sla_status(
        db: Session,
        sla_tracking_id: UUID,
        status: SLAStatus,
        breached_at: Optional[datetime] = None
    ) -> Optional[TaskSLATracking]:
        """Update SLA tracking status"""
        tracking = db.query(TaskSLATracking).filter(
            TaskSLATracking.id == sla_tracking_id
        ).first()
        if tracking:
            tracking.sla_status = status
            if breached_at:
                tracking.breached_at = breached_at
            db.commit()
            db.refresh(tracking)
        return tracking

