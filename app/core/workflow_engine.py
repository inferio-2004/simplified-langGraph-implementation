from typing import Dict, List, Any, Optional, Callable, Union
import asyncio
import logging
import uuid
from datetime import datetime
from dataclasses import dataclass

from .state import WorkflowState, WorkflowRun, NodeExecution, NodeStatus
from .tools import tool_registry, ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class Edge:
    """Represents a connection between nodes"""
    from_node: str
    to_node: str
    condition: Optional[Callable[[WorkflowState], bool]] = None
    condition_key: Optional[str] = None
    condition_value: Any = None


@dataclass 
class Node:
    """Represents a workflow node"""
    id: str
    tool_name: str
    params: Dict[str, Any]
    description: str = ""


class ConditionalRouter:
    """Handles conditional routing logic"""
    
    @staticmethod
    def create_condition(condition_type: str, key: str, value: Any) -> Callable[[WorkflowState], bool]:
        """Create a condition function"""
        def condition_func(state: WorkflowState) -> bool:
            state_value = state.get(key)
            
            # Resolve value if it's a state reference
            if isinstance(value, str) and value.startswith("$state."):
                state_key = value[7:]  # Remove "$state." prefix
                comparison_value = state.get(state_key)
            else:
                comparison_value = value
            
            if condition_type == "eq":
                return state_value == comparison_value
            elif condition_type == "gt":
                return state_value is not None and comparison_value is not None and state_value > comparison_value
            elif condition_type == "lt": 
                return state_value is not None and comparison_value is not None and state_value < comparison_value
            elif condition_type == "gte":
                return state_value is not None and comparison_value is not None and state_value >= comparison_value
            elif condition_type == "lte":
                return state_value is not None and comparison_value is not None and state_value <= comparison_value
            elif condition_type == "exists":
                return state_value is not None
            elif condition_type == "not_exists":
                return state_value is None
            else:
                return False
        
        return condition_func


class WorkflowEngine:
    """Core workflow execution engine"""
    
    def __init__(self, tool_registry: ToolRegistry = None):
        self.tool_registry = tool_registry or tool_registry
        self.graphs: Dict[str, 'WorkflowGraph'] = {}
        self.runs: Dict[str, WorkflowRun] = {}
        self.event_listeners: List[Callable] = []
    
    def add_event_listener(self, listener: Callable) -> None:
        """Add event listener for workflow events"""
        self.event_listeners.append(listener)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event to all listeners"""
        for listener in self.event_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event_type, data)
                else:
                    listener(event_type, data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
    
    def create_graph(self, graph_definition: Dict[str, Any]) -> str:
        """Create a new workflow graph"""
        graph_id = str(uuid.uuid4())
        graph = WorkflowGraph.from_definition(graph_definition, self.tool_registry)
        self.graphs[graph_id] = graph
        
        logger.info(f"Created graph {graph_id} with {len(graph.nodes)} nodes")
        return graph_id
    
    async def run_workflow(self, graph_id: str, initial_state: Dict[str, Any]) -> WorkflowRun:
        """Execute a workflow"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        run_id = str(uuid.uuid4())
        
        # Create workflow run
        workflow_run = WorkflowRun(
            run_id=run_id,
            graph_id=graph_id,
            initial_state=WorkflowState(data=initial_state),
            current_state=WorkflowState(data=initial_state.copy())
        )
        
        self.runs[run_id] = workflow_run
        
        # Execute workflow
        try:
            await self.emit_event("workflow_started", {
                "run_id": run_id,
                "graph_id": graph_id
            })
            
            await graph.execute(workflow_run, self.emit_event)
            
            workflow_run.status = NodeStatus.COMPLETED
            workflow_run.completed_at = datetime.now()
            
            await self.emit_event("workflow_completed", {
                "run_id": run_id,
                "status": "completed"
            })
            
        except Exception as e:
            workflow_run.status = NodeStatus.FAILED
            workflow_run.error = str(e)
            workflow_run.completed_at = datetime.now()
            
            await self.emit_event("workflow_failed", {
                "run_id": run_id,
                "error": str(e)
            })
            
            logger.error(f"Workflow {run_id} failed: {e}")
            raise
        
        return workflow_run
    
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Get workflow run by ID"""
        return self.runs.get(run_id)
    
    def get_graph(self, graph_id: str) -> Optional['WorkflowGraph']:
        """Get graph by ID"""
        return self.graphs.get(graph_id)


class WorkflowGraph:
    """Represents a workflow graph with nodes and edges"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.start_node: Optional[str] = None
        self.tool_registry: Optional[ToolRegistry] = None
    
    @classmethod
    def from_definition(cls, definition: Dict[str, Any], tool_registry: ToolRegistry) -> 'WorkflowGraph':
        """Create graph from definition"""
        graph = cls()
        graph.tool_registry = tool_registry
        
        # Add nodes
        for node_def in definition.get("nodes", []):
            node = Node(
                id=node_def["id"],
                tool_name=node_def["tool"],
                params=node_def.get("params", {}),
                description=node_def.get("description", "")
            )
            graph.nodes[node.id] = node
        
        # Add edges
        for edge_def in definition.get("edges", []):
            edge = Edge(
                from_node=edge_def["from"],
                to_node=edge_def["to"]
            )
            
            # Add condition if specified
            if "condition" in edge_def:
                cond = edge_def["condition"]
                edge.condition = ConditionalRouter.create_condition(
                    cond["type"],
                    cond["key"],
                    cond["value"]
                )
            
            graph.edges.append(edge)
        
        # Set start node
        graph.start_node = definition.get("start_node")
        if not graph.start_node and graph.nodes:
            graph.start_node = list(graph.nodes.keys())[0]
        
        return graph
    
    async def execute(self, workflow_run: WorkflowRun, event_emitter: Callable) -> None:
        """Execute the workflow"""
        if not self.start_node:
            raise ValueError("No start node defined")
        
        current_node = self.start_node
        visited_nodes = set()
        max_iterations = 100  # Prevent infinite loops
        iterations = 0
        
        while current_node and iterations < max_iterations:
            iterations += 1
            
            # Check for loops (allow limited loops)
            if current_node in visited_nodes and iterations > 10:
                logger.warning(f"Potential infinite loop detected at node {current_node}")
                break
            
            visited_nodes.add(current_node)
            workflow_run.current_node = current_node
            
            # Execute current node
            await self._execute_node(current_node, workflow_run, event_emitter)
            
            # Find next node
            next_nodes = self._get_next_nodes(current_node, workflow_run.current_state)
            
            if not next_nodes:
                break
            elif len(next_nodes) == 1:
                current_node = next_nodes[0]
            else:
                # Multiple paths - for now, take first valid one
                current_node = next_nodes[0]
                logger.warning(f"Multiple next nodes found, taking first: {current_node}")
    
    async def _execute_node(self, node_id: str, workflow_run: WorkflowRun, event_emitter: Callable) -> None:
        """Execute a single node"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        node = self.nodes[node_id]
        execution = NodeExecution(node_id=node_id)
        execution.status = NodeStatus.RUNNING
        execution.started_at = datetime.now()
        
        workflow_run.node_executions.append(execution)
        
        await event_emitter("node_started", {
            "run_id": workflow_run.run_id,
            "node_id": node_id,
            "tool": node.tool_name
        })
        
        try:
            # Add a small delay to make streaming visible
            await asyncio.sleep(0.3)
            
            # Prepare parameters
            params = node.params.copy()
            
            # Add state data to params if needed
            for key, value in params.items():
                if isinstance(value, str) and value.startswith("$state."):
                    state_key = value[7:]  # Remove "$state." prefix
                    params[key] = workflow_run.current_state.get(state_key)
            
            # Execute tool
            result = await self.tool_registry.execute(node.tool_name, **params)
            
            # Update state with result
            if isinstance(result, dict):
                workflow_run.current_state.update(result)
            else:
                workflow_run.current_state.set(f"{node_id}_result", result)
            
            execution.status = NodeStatus.COMPLETED
            execution.output = {"result": result}
            execution.completed_at = datetime.now()
            
            await event_emitter("node_completed", {
                "run_id": workflow_run.run_id,
                "node_id": node_id,
                "result": result
            })
            
            logger.info(f"Node {node_id} completed successfully")
            
        except Exception as e:
            execution.status = NodeStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now()
            
            await event_emitter("node_failed", {
                "run_id": workflow_run.run_id,
                "node_id": node_id,
                "error": str(e)
            })
            
            logger.error(f"Node {node_id} failed: {e}")
            raise
    
    def _get_next_nodes(self, current_node: str, state: WorkflowState) -> List[str]:
        """Get next nodes based on edges and conditions"""
        next_nodes = []
        
        for edge in self.edges:
            if edge.from_node == current_node:
                # Check condition if present
                if edge.condition:
                    if edge.condition(state):
                        next_nodes.append(edge.to_node)
                else:
                    next_nodes.append(edge.to_node)
        
        return next_nodes