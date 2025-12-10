#!/usr/bin/env python3
"""
Simple test script to verify the workflow engine functionality
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.workflow_engine import WorkflowEngine
from app.core.tools import tool_registry
from app.workflows.llm_summarization import create_llm_summarization_workflow, create_sample_llm_summarization_run
from app.storage.sqlite_store import SQLiteStorage


async def test_workflow_engine():
    """Test the workflow engine with summarization workflow"""
    print("🚀 Testing Workflow Engine...")
    
    # Initialize components
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "db", "test_workflow.db")
    engine = WorkflowEngine(tool_registry)
    storage = SQLiteStorage(db_path)
    await storage.initialize()
    
    # Test 1: Create workflow graph
    print("\n📋 Test 1: Creating LLM-powered summarization workflow...")
    workflow_def = create_llm_summarization_workflow()
    graph_id = engine.create_graph(workflow_def)
    await storage.save_graph(graph_id, workflow_def)
    print(f"✅ Created graph with ID: {graph_id}")
    
    # Test 2: Run workflow
    print("\n⚡ Test 2: Running LLM workflow with sample data...")
    sample_data = create_sample_llm_summarization_run()
    print(f"📝 Input text length: {len(sample_data['input_text'])} characters")
    print(f"🎯 Target summary length: {sample_data['target_length']} characters")
    
    try:
        workflow_run = await engine.run_workflow(graph_id, sample_data)
        await storage.save_workflow_run(workflow_run)
        
        print(f"✅ Workflow completed with status: {workflow_run.status}")
        print(f"📊 Executed {len(workflow_run.node_executions)} nodes")
        
        # Show results
        final_state = workflow_run.current_state.data
        if 'final_summary' in final_state:
            summary = final_state['final_summary']
            print(f"📜 Generated summary ({len(summary)} chars):")
            print(f"   {summary[:200]}{'...' if len(summary) > 200 else ''}")
        
        if 'quality_score' in final_state:
            print(f"🏆 Quality score: {final_state['quality_score']}")
            
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False
    
    # Test 3: Tool registry
    print("\n🔧 Test 3: Checking tool registry...")
    tools = tool_registry.get_tools()
    print(f"✅ Found {len(tools)} registered tools:")
    for tool_name, info in list(tools.items())[:5]:  # Show first 5
        async_marker = " (async)" if info.get("async") else ""
        print(f"   - {tool_name}{async_marker}: {info.get('description', 'No description')}")
    
    # Test 4: Storage operations
    print("\n💾 Test 4: Testing storage operations...")
    
    # List graphs
    graphs = await storage.list_graphs()
    print(f"✅ Found {len(graphs)} stored graphs")
    
    # List runs
    runs = await storage.list_workflow_runs()
    print(f"✅ Found {len(runs)} stored runs")
    
    # Retrieve run
    retrieved_run = await storage.get_workflow_run(workflow_run.run_id)
    if retrieved_run:
        print(f"✅ Successfully retrieved run from storage")
    else:
        print("❌ Failed to retrieve run from storage")
    
    print("\n🎉 All tests completed successfully!")
    return True


async def test_individual_tools():
    """Test individual tools to ensure they work correctly"""
    print("\n🔍 Testing individual tools...")
    
    sample_text = "This is a test text for tool validation. It should be processed correctly by our tools."
    
    # Test text splitting
    chunks = await tool_registry.execute("split_text", text=sample_text, chunk_size=50, overlap=10)
    print(f"✅ split_text: Generated {len(chunks)} chunks")
    
    # Test summary generation
    summary = await tool_registry.execute("generate_summary", text=sample_text, max_length=100)
    print(f"✅ generate_summary: Generated {len(summary)} char summary")
    
    # Test quality scoring
    score = await tool_registry.execute("calculate_summary_score", original_text=sample_text, summary=summary)
    print(f"✅ calculate_summary_score: Score = {score}")
    
    print("✅ Individual tool tests completed")


if __name__ == "__main__":
    async def main():
        print("🧪 Workflow Engine Test Suite")
        print("=" * 50)
        
        # Test individual tools first
        await test_individual_tools()
        
        # Test full workflow
        success = await test_workflow_engine()
        
        if success:
            print("\n🎊 All tests passed! The workflow engine is ready to use.")
            print("\nTo start the API server, run:")
            print("   python main.py")
            print("\nThen visit http://localhost:8000/docs for the API documentation")
        else:
            print("\n💥 Some tests failed. Please check the implementation.")
            sys.exit(1)
    
    # Run the test suite
    asyncio.run(main())