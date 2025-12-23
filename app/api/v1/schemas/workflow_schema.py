from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


# ==================== Workflow Template Schemas ====================

class WorkflowNodeCreate(BaseModel):
    """Schema for creating a workflow node"""
    node_key: str = Field(..., min_length=1, max_length=100, description="Unique identifier within workflow")
    node_type: str = Field(..., description="Node type: start, assign, status, action, end")
    role: Optional[str] = Field(None, max_length=100, description="Role required for this node")
    metadata: Optional[Dict[str, Any]] = Field(None, description="SLA, notifications, rules, etc.")
    position_x: int = Field(default=0, description="X position on canvas")
    position_y: int = Field(default=0, description="Y position on canvas")


class WorkflowEdgeCreate(BaseModel):
    """Schema for creating a workflow edge"""
    source_node_key: str = Field(..., description="Source node key")
    target_node_key: str = Field(..., description="Target node key")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condition logic for transition")


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow template"""
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    nodes: List[WorkflowNodeCreate] = Field(..., min_length=1, description="List of workflow nodes")
    edges: List[WorkflowEdgeCreate] = Field(default_factory=list, description="List of workflow edges")
    
    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v):
        """Ensure at least one start node exists"""
        start_nodes = [n for n in v if n.node_type == "start"]
        if not start_nodes:
            raise ValueError("Workflow must have at least one start node")
        return v


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    nodes: Optional[List[WorkflowNodeCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None


class WorkflowNodeResponse(BaseModel):
    """Schema for workflow node response"""
    id: UUID
    node_key: str
    node_type: str
    role: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(None, alias="node_metadata", serialization_alias="metadata")
    position_x: int
    position_y: int
    created_at: datetime
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class WorkflowEdgeResponse(BaseModel):
    """Schema for workflow edge response"""
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    source_node_key: Optional[str] = None
    target_node_key: Optional[str] = None
    condition: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    """Schema for workflow template response"""
    id: UUID
    company_id: int
    name: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    nodes: List[WorkflowNodeResponse] = []
    edges: List[WorkflowEdgeResponse] = []
    
    model_config = {"from_attributes": True}


class WorkflowListItem(BaseModel):
    """Schema for workflow list item"""
    id: UUID
    name: str
    version: int
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== Project Workflow Schemas ====================

class ProjectWorkflowAssign(BaseModel):
    """Schema for assigning workflow to project"""
    workflow_template_id: UUID = Field(..., description="Workflow template ID to assign")


class ProjectWorkflowUserAssign(BaseModel):
    """Schema for assigning user to role in project workflow"""
    role: str = Field(..., min_length=1, max_length=100, description="Role name (e.g., Developer, Tester)")
    user_id: int = Field(..., description="User ID to assign to this role")


class ProjectWorkflowConfigureUsers(BaseModel):
    """Schema for configuring users for project workflow"""
    user_assignments: List[ProjectWorkflowUserAssign] = Field(..., min_length=1, description="List of role-user assignments")


class ProjectWorkflowUserResponse(BaseModel):
    """Schema for project workflow user response"""
    id: UUID
    role: str
    user_id: int
    user: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectWorkflowResponse(BaseModel):
    """Schema for project workflow response"""
    id: UUID
    project_id: int
    workflow_template_id: UUID
    workflow_template: Optional[WorkflowListItem] = None
    users: List[ProjectWorkflowUserResponse] = []
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== Task Workflow Schemas ====================

class TaskCreateWithWorkflow(BaseModel):
    """Schema for creating task with workflow initialization"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field("medium", description="low, medium, high")
    due_date: Optional[datetime] = None


class TaskTransitionRequest(BaseModel):
    """Schema for task transition request"""
    action: Optional[str] = Field(None, description="Action that triggers transition (e.g., approve, reject, complete)")
    condition_data: Optional[Dict[str, Any]] = Field(None, description="Additional data for condition evaluation")


class TaskStateHistoryResponse(BaseModel):
    """Schema for task state history response"""
    id: UUID
    task_id: int
    from_node_id: Optional[UUID]
    to_node_id: UUID
    from_node_key: Optional[str] = None
    to_node_key: Optional[str] = None
    action: Optional[str]
    performed_by: Optional[int]
    performer_name: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TaskWorkflowResponse(BaseModel):
    """Schema for task with workflow information"""
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    project_id: Optional[int]
    current_node_id: Optional[UUID]
    current_node_key: Optional[str] = None
    current_node_type: Optional[str] = None
    current_role: Optional[str] = None
    project_workflow_id: Optional[UUID]
    state_history: List[TaskStateHistoryResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== SLA Schemas ====================

class SLADefinitionCreate(BaseModel):
    """Schema for creating SLA definition"""
    workflow_node_id: UUID = Field(..., description="Workflow node ID")
    response_time_hours: Optional[int] = Field(None, ge=0, description="Response time in hours")
    resolution_time_hours: Optional[int] = Field(None, ge=0, description="Resolution time in hours")
    escalation_role: Optional[str] = Field(None, max_length=100, description="Role to escalate to")


class SLADefinitionResponse(BaseModel):
    """Schema for SLA definition response"""
    id: UUID
    workflow_node_id: UUID
    response_time_hours: Optional[int]
    resolution_time_hours: Optional[int]
    escalation_role: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TaskSLATrackingResponse(BaseModel):
    """Schema for task SLA tracking response"""
    id: UUID
    task_id: int
    workflow_node_id: UUID
    workflow_node_key: Optional[str] = None
    sla_status: str
    started_at: datetime
    response_deadline: Optional[datetime]
    resolution_deadline: Optional[datetime]
    breached_at: Optional[datetime]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TaskSLAResponse(BaseModel):
    """Schema for task SLA status response"""
    task_id: int
    current_sla: Optional[TaskSLATrackingResponse] = None
    all_sla_tracking: List[TaskSLATrackingResponse] = []
    breached_count: int = 0
    met_count: int = 0
    pending_count: int = 0

