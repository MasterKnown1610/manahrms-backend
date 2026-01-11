from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class Workflow(Base):
    """
    Workflow template model - reusable workflow definitions.
    Created once and can be assigned to multiple projects.
    """
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    project_workflows = relationship("ProjectWorkflow", back_populates="workflow_template")
    
    def __repr__(self):
        return f"<Workflow {self.name} v{self.version}>"


class NodeType(str, enum.Enum):
    """Workflow node types"""
    START = "start"
    ASSIGN = "assign"
    STATUS = "status"
    ACTION = "action"
    END = "end"


class WorkflowNode(Base):
    """
    Workflow node model - represents a step in the workflow.
    """
    __tablename__ = "workflow_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False)  # Unique identifier within workflow (e.g., "start_1", "dev_task")
    node_type = Column(SQLEnum(NodeType), nullable=False, index=True)
    role = Column(String(100), nullable=True)  # Role required for this node (e.g., "Developer", "Tester", "Manager")
    node_metadata = Column("metadata", JSONB, nullable=True)  # SLA, notifications, rules, etc.
    position_x = Column(Integer, nullable=False, default=0)
    position_y = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")
    source_edges = relationship("WorkflowEdge", foreign_keys="WorkflowEdge.source_node_id", back_populates="source_node")
    target_edges = relationship("WorkflowEdge", foreign_keys="WorkflowEdge.target_node_id", back_populates="target_node")
    sla_definitions = relationship("SLADefinition", back_populates="workflow_node", cascade="all, delete-orphan")
    task_states = relationship("TaskStateHistory", foreign_keys="TaskStateHistory.from_node_id", back_populates="from_node")
    task_states_to = relationship("TaskStateHistory", foreign_keys="TaskStateHistory.to_node_id", back_populates="to_node")
    task_sla_tracking = relationship("TaskSLATracking", back_populates="workflow_node")
    
    def __repr__(self):
        return f"<WorkflowNode {self.node_key} ({self.node_type})>"


class WorkflowEdge(Base):
    """
    Workflow edge model - represents transitions between nodes.
    """
    __tablename__ = "workflow_edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    condition = Column(JSONB, nullable=True)  # Condition logic for transition (e.g., {"action": "approve", "status": "completed"})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="edges")
    source_node = relationship("WorkflowNode", foreign_keys=[source_node_id], back_populates="source_edges")
    target_node = relationship("WorkflowNode", foreign_keys=[target_node_id], back_populates="target_edges")
    
    def __repr__(self):
        return f"<WorkflowEdge {self.source_node_id} -> {self.target_node_id}>"


class ProjectWorkflow(Base):
    """
    Project workflow instance - links a project to a workflow template.
    When a workflow is assigned to a project, nodes are duplicated for project-specific configuration.
    """
    __tablename__ = "project_workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_template_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="project_workflows")
    workflow_template = relationship("Workflow", back_populates="project_workflows")
    users = relationship("ProjectWorkflowUser", back_populates="project_workflow", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project_workflow")
    
    def __repr__(self):
        return f"<ProjectWorkflow Project:{self.project_id} Workflow:{self.workflow_template_id}>"


class ProjectWorkflowUser(Base):
    """
    Project workflow user assignment - assigns users to roles for a specific project workflow.
    """
    __tablename__ = "project_workflow_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_workflow_id = Column(UUID(as_uuid=True), ForeignKey("project_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(100), nullable=False, index=True)  # Role name (e.g., "Developer", "Tester", "Manager")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project_workflow = relationship("ProjectWorkflow", back_populates="users")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ProjectWorkflowUser Role:{self.role} User:{self.user_id}>"


class TaskStateHistory(Base):
    """
    Task state history - tracks all transitions a task makes through workflow nodes.
    """
    __tablename__ = "task_state_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    from_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True)
    to_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=False, index=True)
    action = Column(String(100), nullable=True)  # Action that triggered transition (e.g., "approve", "reject", "complete")
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    task = relationship("Task", back_populates="state_history")
    from_node = relationship("WorkflowNode", foreign_keys=[from_node_id], back_populates="task_states")
    to_node = relationship("WorkflowNode", foreign_keys=[to_node_id], back_populates="task_states_to")
    performer = relationship("User", foreign_keys=[performed_by])
    
    def __repr__(self):
        return f"<TaskStateHistory Task:{self.task_id} {self.from_node_id} -> {self.to_node_id}>"


class SLADefinition(Base):
    """
    SLA definition - defines SLA rules for workflow nodes.
    """
    __tablename__ = "sla_definitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workflow_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    response_time_hours = Column(Integer, nullable=True)  # Time to acknowledge/respond
    resolution_time_hours = Column(Integer, nullable=True)  # Time to complete/resolve
    escalation_role = Column(String(100), nullable=True)  # Role to escalate to if SLA breached
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workflow_node = relationship("WorkflowNode", back_populates="sla_definitions")
    
    def __repr__(self):
        return f"<SLADefinition Node:{self.workflow_node_id}>"


class SLAStatus(str, enum.Enum):
    """SLA tracking status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    MET = "met"
    BREACHED = "breached"
    ESCALATED = "escalated"


class TaskSLATracking(Base):
    """
    Task SLA tracking - tracks SLA status for tasks at each workflow node.
    """
    __tablename__ = "task_sla_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_node_id = Column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=False, index=True)
    sla_status = Column(SQLEnum(SLAStatus), default=SLAStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    response_deadline = Column(DateTime, nullable=True)
    resolution_deadline = Column(DateTime, nullable=True)
    breached_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="sla_tracking")
    workflow_node = relationship("WorkflowNode", back_populates="task_sla_tracking")
    
    def __repr__(self):
        return f"<TaskSLATracking Task:{self.task_id} Node:{self.workflow_node_id} Status:{self.sla_status}>"

