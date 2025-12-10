# Tests

This folder contains all test files for the LangGraph workflow engine.

## Test Files

### Core Tests
- **`test_workflow.py`** - Basic workflow engine tests (rule-based and LLM workflows)
- **`test_websocket.py`** - WebSocket streaming functionality tests

### Interactive Tests  
- **`test_interactive.py`** - Interactive testing with user input (choose between rule-based and LLM)
- **`test_quick.py`** - Quick LLM workflow test with sample data

## Running Tests

From the project root directory:

```bash
# Quick LLM workflow test
python tests/test_quick.py

# Interactive testing (choose workflow type)
python tests/test_interactive.py

# Core workflow engine tests
python tests/test_workflow.py

# WebSocket streaming tests (requires server running)
python tests/test_websocket.py
```

## Test Features

- ✅ LLM-powered intelligent summarization (Groq llama-3.1-8b-instant)
- ✅ Rule-based fallback summarization
- ✅ Multi-node workflow orchestration
- ✅ WebSocket real-time streaming
- ✅ Quality assessment and refinement loops
- ✅ Conditional routing based on quality scores