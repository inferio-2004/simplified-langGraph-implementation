from typing import Dict, List, Any, Optional, Callable, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowState(BaseModel):
    """Base state that flows through the workflow"""
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state data"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in state data"""
        self.data[key] = value
        self.updated_at = datetime.now()
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple values in state"""
        self.data.update(updates)
        self.updated_at = datetime.now()


class NodeExecution(BaseModel):
    """Tracks execution of a single node"""
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    logs: List[str] = Field(default_factory=list)


class WorkflowRun(BaseModel):
    """Tracks a complete workflow execution"""
    run_id: str
    graph_id: str
    status: NodeStatus = NodeStatus.PENDING
    initial_state: WorkflowState
    current_state: WorkflowState
    node_executions: List[NodeExecution] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    current_node: Optional[str] = None
    error: Optional[str] = None