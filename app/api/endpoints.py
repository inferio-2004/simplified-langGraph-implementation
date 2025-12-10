from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import json
import asyncio
import logging

from ..core.workflow_engine import WorkflowEngine
from ..core.tools import tool_registry
from ..storage.sqlite_store import SQLiteStorage
from .models import (
    GraphCreateRequest, GraphCreateResponse,
    WorkflowRunRequest, WorkflowRunResponse,
    WorkflowStatusResponse, NodeExecutionInfo,
    GraphListResponse, RunListResponse,
    ToolListResponse, ToolInfo, WebSocketEvent
)

logger = logging.getLogger(__name__)

# Global instances
workflow_engine = WorkflowEngine(tool_registry)
storage = SQLiteStorage("db/workflow.db")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        self.active_connections[run_id] = websocket
        logger.info(f"WebSocket connected for run {run_id}")
    
    def disconnect(self, run_id: str):
        if run_id in self.active_connections:
            del self.active_connections[run_id]
            logger.info(f"WebSocket disconnected for run {run_id}")
    
    async def send_event(self, run_id: str, event_type: str, data: Dict[str, Any]):
        if run_id in self.active_connections:
            websocket = self.active_connections[run_id]
            try:
                event = WebSocketEvent(event_type=event_type, data=data)
                await websocket.send_text(event.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to send WebSocket event: {e}")
                self.disconnect(run_id)

connection_manager = ConnectionManager()

# Event listener for workflow events
async def workflow_event_listener(event_type: str, data: Dict[str, Any]):
    """Listen to workflow events and broadcast via WebSocket"""
    run_id = data.get("run_id")
    if run_id:
        await connection_manager.send_event(run_id, event_type, data)
        
        # Save workflow state for major events
        if event_type in ["workflow_started", "node_completed", "workflow_completed", "workflow_failed"]:
            workflow_run = workflow_engine.get_run(run_id)
            if workflow_run:
                try:
                    await storage.save_workflow_run(workflow_run)
                except Exception as e:
                    logger.error(f"Failed to save workflow run: {e}")

# Register event listener
workflow_engine.add_event_listener(workflow_event_listener)

# Create router
router = APIRouter()


@router.on_event("startup")
async def startup_event():
    """Initialize storage on startup"""
    await storage.initialize()
    logger.info("API started successfully")


@router.post("/graph/create", response_model=GraphCreateResponse)
async def create_graph(request: GraphCreateRequest):
    """Create a new workflow graph"""
    try:
        # Convert to dict for engine
        definition = request.definition.model_dump()
        
        # Create graph
        graph_id = workflow_engine.create_graph(definition)
        
        # Save to storage
        await storage.save_graph(graph_id, definition)
        
        return GraphCreateResponse(graph_id=graph_id)
        
    except Exception as e:
        logger.error(f"Failed to create graph: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/graph/run", response_model=WorkflowRunResponse)
async def run_workflow(request: WorkflowRunRequest):
    """Run a workflow"""
    try:
        # Create a run ID immediately
        import uuid
        run_id = str(uuid.uuid4())
        
        # Start workflow execution in background
        asyncio.create_task(
            _execute_workflow_async(request.graph_id, request.initial_state, run_id)
        )
        
        # Return run information immediately
        return WorkflowRunResponse(
            run_id=run_id,
            status="starting",
            message="Workflow execution started"
        )
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def _execute_workflow_async(graph_id: str, initial_state: Dict[str, Any], run_id: str):
    """Execute workflow asynchronously"""
    try:
        # Add a small delay to ensure WebSocket can connect
        await asyncio.sleep(0.5)
        
        # Create workflow run with predetermined ID
        from ..core.state import WorkflowRun, WorkflowState
        workflow_run = WorkflowRun(
            run_id=run_id,
            graph_id=graph_id,
            initial_state=WorkflowState(data=initial_state),
            current_state=WorkflowState(data=initial_state.copy())
        )
        
        # Store the run immediately
        workflow_engine.runs[run_id] = workflow_run
        
        # Execute the workflow
        graph = workflow_engine.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
            
        await graph.execute(workflow_run, workflow_engine.emit_event)
        
        # Update final status
        from ..core.state import NodeStatus
        from datetime import datetime
        workflow_run.status = NodeStatus.COMPLETED
        workflow_run.completed_at = datetime.now()
        
        # Save to storage
        await storage.save_workflow_run(workflow_run)
        
        # Emit completion event
        await workflow_engine.emit_event("workflow_completed", {
            "run_id": run_id,
            "status": "completed"
        })
        
        logger.info(f"Workflow {run_id} completed successfully")
        
    except Exception as e:
        # Handle workflow failure
        from ..core.state import NodeStatus
        from datetime import datetime
        
        if run_id in workflow_engine.runs:
            workflow_run = workflow_engine.runs[run_id]
            workflow_run.status = NodeStatus.FAILED
            workflow_run.error = str(e)
            workflow_run.completed_at = datetime.now()
            await storage.save_workflow_run(workflow_run)
        
        await workflow_engine.emit_event("workflow_failed", {
            "run_id": run_id,
            "error": str(e)
        })
        
        logger.error(f"Workflow {run_id} failed: {e}")


@router.get("/graph/state/{run_id}", response_model=WorkflowStatusResponse)
async def get_workflow_state(run_id: str):
    """Get current state of a workflow run"""
    # First try in-memory
    workflow_run = workflow_engine.get_run(run_id)
    
    # If not found, try storage
    if not workflow_run:
        workflow_run = await storage.get_workflow_run(run_id)
    
    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    
    # Convert node executions
    node_executions = [
        NodeExecutionInfo(
            node_id=exec.node_id,
            status=exec.status,
            started_at=exec.started_at,
            completed_at=exec.completed_at,
            error=exec.error,
            output=exec.output
        )
        for exec in workflow_run.node_executions
    ]
    
    return WorkflowStatusResponse(
        run_id=workflow_run.run_id,
        graph_id=workflow_run.graph_id,
        status=workflow_run.status,
        current_node=workflow_run.current_node,
        current_state=workflow_run.current_state.data,
        node_executions=node_executions,
        created_at=workflow_run.created_at,
        completed_at=workflow_run.completed_at,
        error=workflow_run.error
    )


@router.get("/graphs", response_model=GraphListResponse)
async def list_graphs():
    """List all workflow graphs"""
    try:
        graphs = await storage.list_graphs()
        return GraphListResponse(graphs=graphs)
    except Exception as e:
        logger.error(f"Failed to list graphs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs", response_model=RunListResponse)
async def list_runs(graph_id: Optional[str] = None):
    """List workflow runs, optionally filtered by graph_id"""
    try:
        runs = await storage.list_workflow_runs(graph_id)
        return RunListResponse(runs=runs)
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List all available tools"""
    try:
        tools_dict = tool_registry.get_tools()
        tools = [
            ToolInfo(
                name=name,
                description=info.get("description", ""),
                async_func=info.get("async", False),
                available=info.get("available", True)
            )
            for name, info in tools_dict.items()
        ]
        return ToolListResponse(tools=tools)
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/graph/{graph_id}")
async def delete_graph(graph_id: str):
    """Delete a workflow graph"""
    try:
        success = await storage.delete_graph(graph_id)
        if success:
            # Also remove from engine
            if graph_id in workflow_engine.graphs:
                del workflow_engine.graphs[graph_id]
            return {"message": "Graph deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Graph not found")
    except Exception as e:
        logger.error(f"Failed to delete graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/run/{run_id}")
async def delete_run(run_id: str):
    """Delete a workflow run"""
    try:
        success = await storage.delete_workflow_run(run_id)
        if success:
            # Also remove from engine
            if run_id in workflow_engine.runs:
                del workflow_engine.runs[run_id]
            return {"message": "Run deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Run not found")
    except Exception as e:
        logger.error(f"Failed to delete run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for streaming workflow events"""
    await connection_manager.connect(websocket, run_id)
    
    try:
        # Send initial connection event
        await connection_manager.send_event(run_id, "connected", {
            "run_id": run_id,
            "message": "WebSocket connected"
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await connection_manager.send_event(run_id, "pong", {
                        "run_id": run_id,
                        "message": "pong"
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await connection_manager.send_event(run_id, "error", {
                    "run_id": run_id,
                    "error": str(e)
                })
                
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(run_id)