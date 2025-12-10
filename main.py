from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from contextlib import asynccontextmanager

from app.api.endpoints import router, storage
from app.workflows.summarization import create_summarization_workflow, create_sample_summarization_run
from app.workflows.llm_summarization import create_llm_summarization_workflow, create_sample_llm_summarization_run
from app.api.endpoints import workflow_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting workflow engine application...")
    
    # Initialize storage
    await storage.initialize()
    
    # Register both workflows
    try:
        # Original rule-based workflow
        workflow_def = create_summarization_workflow()
        default_graph_id = workflow_engine.create_graph(workflow_def)
        await storage.save_graph(default_graph_id, workflow_def)
        app.state.default_graph_id = default_graph_id
        
        # LLM-powered workflow
        llm_workflow_def = create_llm_summarization_workflow()
        llm_graph_id = workflow_engine.create_graph(llm_workflow_def)
        await storage.save_graph(llm_graph_id, llm_workflow_def)
        app.state.llm_graph_id = llm_graph_id
        
        logger.info(f"Registered rule-based workflow: {default_graph_id}")
        logger.info(f"Registered LLM workflow: {llm_graph_id}")
        
    except Exception as e:
        logger.error(f"Failed to register workflows: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title="Workflow Engine API",
    description="A simplified LangGraph-like workflow engine for orchestrating multi-step processes",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["workflows"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Workflow Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "create_graph": "POST /api/v1/graph/create",
            "run_workflow": "POST /api/v1/graph/run", 
            "get_state": "GET /api/v1/graph/state/{run_id}",
            "list_graphs": "GET /api/v1/graphs",
            "list_runs": "GET /api/v1/runs",
            "list_tools": "GET /api/v1/tools",
            "websocket": "WS /api/v1/ws/{run_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "workflow-engine"}


@app.post("/demo/summarization")
async def demo_summarization():
    """Demo endpoint to run the summarization workflow with sample data"""
    try:
        # Get or create the default summarization workflow
        if not hasattr(app.state, 'default_graph_id'):
            # Create one if it doesn't exist
            workflow_def = create_summarization_workflow()
            graph_id = workflow_engine.create_graph(workflow_def)
            await storage.save_graph(graph_id, workflow_def)
            app.state.default_graph_id = graph_id
        else:
            graph_id = app.state.default_graph_id
        
        # Get sample data
        sample_data = create_sample_summarization_run()
        
        # Start workflow execution
        task = asyncio.create_task(
            workflow_engine.run_workflow(graph_id, sample_data)
        )
        
        # Return run information
        return {
            "message": "Demo summarization workflow started",
            "graph_id": graph_id,
            "sample_data": sample_data,
            "note": "Use GET /api/v1/runs to see execution results"
        }
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo/llm-summarization")
async def demo_llm_summarization():
    """Demo endpoint to run the LLM-powered summarization workflow"""
    try:
        # Get or create the LLM workflow
        if not hasattr(app.state, 'llm_graph_id'):
            # Create one if it doesn't exist
            workflow_def = create_llm_summarization_workflow()
            graph_id = workflow_engine.create_graph(workflow_def)
            await storage.save_graph(graph_id, workflow_def)
            app.state.llm_graph_id = graph_id
        else:
            graph_id = app.state.llm_graph_id
        
        # Get sample data
        sample_data = create_sample_llm_summarization_run()
        
        # Start workflow execution
        task = asyncio.create_task(
            workflow_engine.run_workflow(graph_id, sample_data)
        )
        
        # Return run information
        return {
            "message": "Demo LLM summarization workflow started",
            "graph_id": graph_id,
            "sample_data": sample_data,
            "note": "This uses Groq LLM for high-quality summaries. Use WebSocket to see real-time progress!",
            "websocket_tip": f"Connect to ws://localhost:8000/api/v1/ws/{{run_id}} for streaming"
        }
        
    except Exception as e:
        logger.error(f"LLM demo failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )