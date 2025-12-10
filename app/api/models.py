from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from ..core.state import NodeStatus


class GraphDefinition(BaseModel):
    """Graph definition for API"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    start_node: Optional[str] = None
    description: str = ""


class GraphCreateRequest(BaseModel):
    """Request to create a new graph"""
    definition: GraphDefinition


class GraphCreateResponse(BaseModel):
    """Response for graph creation"""
    graph_id: str
    message: str = "Graph created successfully"


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow"""
    graph_id: str
    initial_state: Dict[str, Any]


class WorkflowRunResponse(BaseModel):
    """Response for workflow run"""
    run_id: str
    status: str
    message: str = "Workflow started"


class NodeExecutionInfo(BaseModel):
    """Node execution information for API"""
    node_id: str
    status: NodeStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status"""
    run_id: str
    graph_id: str
    status: NodeStatus
    current_node: Optional[str] = None
    current_state: Dict[str, Any]
    node_executions: List[NodeExecutionInfo]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class GraphListResponse(BaseModel):
    """Response for graph list"""
    graphs: List[Dict[str, Any]]


class RunListResponse(BaseModel):
    """Response for run list"""
    runs: List[Dict[str, Any]]


class ToolInfo(BaseModel):
    """Tool information for API"""
    name: str
    description: str
    async_func: bool
    available: bool


class ToolListResponse(BaseModel):
    """Response for tool list"""
    tools: List[ToolInfo]


class WebSocketEvent(BaseModel):
    """WebSocket event structure"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)