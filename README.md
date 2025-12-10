# Workflow Engine - Simplified LangGraph Implementation

A lightweight workflow engine that orchestrates multi-step processes through a graph-based architecture. Built with FastAPI, this system supports asynchronous execution, real-time monitoring via WebSockets, and persistent storage with SQLite.

## 🚀 Features

### Core Engine Capabilities
- **Node-based Workflow Execution**: Define workflows as graphs with nodes and edges
- **Shared State Management**: Pydantic-based state that flows between nodes
- **Conditional Routing**: Branch workflows based on state conditions
- **Loop Support**: Repeat nodes until conditions are met
- **Tool Registry**: Extensible system for registering reusable functions

### API & Communication
- **RESTful API**: Complete CRUD operations for graphs and runs
- **WebSocket Streaming**: Real-time workflow event broadcasting
- **Async Execution**: Non-blocking workflow processing
- **SQLite Persistence**: Reliable storage for graphs and execution history

### Example Implementation
- **Text Summarization Pipeline**: Complete workflow demonstrating:
  - Text chunking and parallel processing
  - Iterative refinement with quality assessment
  - Conditional looping until target criteria met

## 📁 Project Structure

```
app/
├── core/
│   ├── workflow_engine.py    # Core graph execution engine
│   ├── state.py             # Pydantic state models
│   └── tools.py             # Tool registry and built-in tools
├── api/
│   ├── endpoints.py         # FastAPI route handlers  
│   └── models.py            # API request/response models
├── workflows/
│   └── summarization.py     # Example summarization workflow
├── storage/
│   └── sqlite_store.py      # SQLite persistence layer
└── main.py                  # FastAPI application entry point
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Quick Start

1. **Clone and navigate to project**
   ```bash
   git clone <repository-url>
   cd tredence_langgraph
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**
   ```bash
   python main.py
   ```

4. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Demo Endpoint: http://localhost:8000/demo/summarization

## 🔧 API Usage

### Core Endpoints

**Create Workflow Graph**
```http
POST /api/v1/graph/create
Content-Type: application/json

{
  "definition": {
    "nodes": [
      {
        "id": "process_step",
        "tool": "my_tool",
        "params": {"input": "$state.data"}
      }
    ],
    "edges": [
      {"from": "process_step", "to": "next_step"}
    ],
    "start_node": "process_step"
  }
}
```

**Execute Workflow**
```http
POST /api/v1/graph/run
Content-Type: application/json

{
  "graph_id": "workflow-uuid",
  "initial_state": {
    "input_text": "Text to process...",
    "target_length": 300
  }
}
```

**Monitor Execution**
```http
GET /api/v1/graph/state/{run_id}
```

**Real-time Updates**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/{run_id}');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Workflow event:', update.event_type, update.data);
};
```

## 💡 Workflow Definition Guide

### Node Structure
```json
{
  "id": "unique_node_name",
  "tool": "registered_tool_name", 
  "description": "What this step does",
  "params": {
    "param_name": "static_value",
    "state_param": "$state.key_name"
  }
}
```

### Edge with Conditions
```json
{
  "from": "source_node",
  "to": "target_node", 
  "condition": {
    "type": "gt|lt|eq|gte|lte|exists|not_exists",
    "key": "state_key",
    "value": "comparison_value"
  }
}
```

### Example: Summarization Workflow
The included summarization workflow demonstrates:

1. **Text Splitting**: Break large text into manageable chunks
2. **Parallel Processing**: Generate summaries for each chunk  
3. **Merging**: Combine individual summaries
4. **Refinement**: Polish and optimize the final summary
5. **Quality Loop**: Repeat refinement until length/quality targets met

## 🔍 Built-in Tools

### Text Processing Tools
- `split_text`: Divide text into overlapping chunks
- `generate_summary`: Create extractive summaries (async)
- `merge_summaries`: Combine multiple summaries
- `refine_summary`: Polish and shorten summaries (async)
- `calculate_summary_score`: Assess summary quality

### Workflow Control Tools  
- `process_chunks`: Batch process multiple text chunks
- `quality_assessment`: Evaluate results and determine next steps

## 📊 Monitoring & Observability

### WebSocket Events
- `workflow_started`: Execution begins
- `node_started`: Individual step begins
- `node_completed`: Step finishes successfully
- `node_failed`: Step encounters error
- `workflow_completed`: Full workflow succeeds
- `workflow_failed`: Workflow encounters fatal error

### Execution Tracking
Each workflow run captures:
- Node execution timestamps
- State transitions
- Error messages and stack traces  
- Output from each processing step

## 🏗️ Architecture Decisions

### Why SQLite?
- **Simplicity**: No external database setup required
- **Persistence**: Survives application restarts
- **Performance**: Adequate for development and small-scale production
- **Async Support**: aiosqlite enables non-blocking database operations

### State Management
- **Pydantic Models**: Type safety and validation
- **Immutable Principles**: State changes tracked through versioning
- **Flexible Storage**: Supports arbitrary data structures via JSON

### Tool Registry Pattern
- **Decorator-based Registration**: Clean tool definition syntax
- **Async/Sync Support**: Accommodates different execution patterns
- **Extensibility**: Easy addition of custom processing functions

## 🚧 Future Enhancements

Given more development time, potential improvements include:

### Scalability Features
- **Distributed Execution**: Celery/Redis for multi-worker processing
- **Database Options**: PostgreSQL support for larger deployments
- **Caching Layer**: Redis integration for state and result caching

### Advanced Workflow Features
- **Parallel Execution**: Concurrent node processing
- **Sub-workflows**: Nested workflow composition
- **Dynamic Graphs**: Runtime graph modification
- **Rollback Support**: State checkpointing and recovery

### Developer Experience
- **Visual Editor**: Web-based graph designer
- **Workflow Templates**: Pre-built common patterns
- **Enhanced Monitoring**: Prometheus/Grafana integration
- **Testing Framework**: Unit/integration testing helpers

### Enterprise Features
- **Authentication**: User/API key management
- **Multi-tenancy**: Isolated workflow spaces
- **Audit Logging**: Comprehensive operation tracking
- **Resource Limits**: Execution time and memory controls

## 🧪 Testing

**Run the demo workflow:**
```bash
curl -X POST http://localhost:8000/demo/summarization
```

**Monitor via WebSocket:**
```bash
# Install wscat: npm install -g wscat
wscat -c ws://localhost:8000/api/v1/ws/{run_id}
```

**Check execution results:**
```bash
curl http://localhost:8000/api/v1/runs
```

## 📝 License

This project is part of a coding assignment demonstrating workflow engine architecture and implementation patterns.

---

**Built with**: FastAPI, SQLAlchemy, Pydantic, WebSockets, SQLite