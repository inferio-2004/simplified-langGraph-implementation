#!/usr/bin/env python3
"""
Quick LLM Workflow Test - Default test using LLM-powered summarization
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.workflow_engine import WorkflowEngine
from app.core.tools import tool_registry
from app.workflows.llm_summarization import create_llm_summarization_workflow
from app.storage.sqlite_store import SQLiteStorage

async def main():
    """Quick test of the LLM-powered workflow system"""
    print("🤖 Quick LLM Workflow Test")
    print("=" * 50)
    
    # Initialize components
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "db", "test_llm_quick.db")
    engine = WorkflowEngine(tool_registry)
    storage = SQLiteStorage(db_path)
    await storage.initialize()
    
    # Create LLM-powered workflow
    print("\n📋 Creating LLM-powered summarization workflow...")
    workflow_def = create_llm_summarization_workflow()
    graph_id = engine.create_graph(workflow_def)
    print(f"✅ Created LLM workflow with ID: {graph_id}")
    
    # Test data
    test_text = """
    Artificial Intelligence (AI) has revolutionized numerous industries in recent years. Machine learning algorithms enable computers to learn from data without explicit programming. Deep learning, a subset of machine learning, uses neural networks with multiple layers to process complex patterns. Natural language processing allows machines to understand and generate human language. Computer vision enables machines to interpret visual information. These technologies have applications in healthcare, finance, transportation, and entertainment. AI systems can now diagnose diseases, detect fraud, power autonomous vehicles, and create realistic content. However, ethical considerations around AI bias, privacy, and job displacement remain important challenges to address.
    """
    
    # Run workflow with LLM
    print("\n⚡ Running LLM-powered summarization...")
    print(f"📝 Input text length: {len(test_text)} characters")
    
    execution_data = {
        "input_text": test_text.strip(),
        "target_length": 200,
        "quality_threshold": 0.7
    }
    
    # Execute workflow
    try:
        result = await engine.run_workflow(graph_id, execution_data)
        
        print(f"\n🎯 Execution Result:")
        print(f"✅ Status: {result.status}")
        print(f"📊 Final summary: {result.current_state.get('final_summary', 'No summary generated')}")
        print(f"📏 Summary length: {len(result.current_state.get('final_summary', ''))}")
        print(f"🔍 Quality score: {result.current_state.get('quality_score', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
    
    print("\n🎉 LLM Quick test completed!")

if __name__ == "__main__":
    asyncio.run(main())