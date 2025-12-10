#!/usr/bin/env python3
"""
Interactive LLM Workflow Test - Choose between rule-based and LLM-powered workflows
"""
import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.workflow_engine import WorkflowEngine
from app.core.tools import tool_registry
from app.workflows.summarization import create_summarization_workflow
from app.workflows.llm_summarization import create_llm_summarization_workflow
from app.storage.sqlite_store import SQLiteStorage


async def interactive_test():
    """Interactive workflow testing with user input"""
    print("🤖 Interactive Workflow Test")
    print("=" * 50)
    print("Choose between rule-based and LLM-powered summarization\n")
    
    # Initialize components
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "db", "test_interactive.db")
    engine = WorkflowEngine(tool_registry)
    storage = SQLiteStorage(db_path)
    await storage.initialize()
    
    while True:
        print("\n" + "="*50)
        print("📋 WORKFLOW OPTIONS:")
        print("1. Rule-based Summarization (fast, deterministic)")
        print("2. LLM-Powered Summarization (intelligent, context-aware) 🤖")
        print("3. Exit")
        
        # Choose workflow
        workflow_choice = input("\nChoose workflow (1/2/3): ").strip()
        
        if workflow_choice == "3":
            print("👋 Goodbye!")
            break
        elif workflow_choice == "1":
            workflow = create_summarization_workflow()
            workflow_name = "Rule-based Summarization"
        elif workflow_choice == "2":
            workflow = create_llm_summarization_workflow()
            workflow_name = "LLM-Powered Summarization 🤖"
        else:
            print("❌ Invalid choice. Using LLM workflow.")
            workflow = create_llm_summarization_workflow()
            workflow_name = "LLM-Powered Summarization 🤖"
        
        # Create workflow graph
        graph_id = engine.create_graph(workflow)
        print(f"✅ Created workflow: {workflow_name}")
        print(f"🆔 Graph ID: {graph_id}")
        
        # Get user input
        print(f"\n📝 INPUT:")
        print("Enter text to summarize (or 'sample' for sample text):")
        user_input = input("> ").strip()
        
        if user_input.lower() == 'sample':
            input_text = """
            Climate change represents one of the most pressing challenges of our time. Rising global temperatures are causing widespread environmental changes including melting ice caps, rising sea levels, and extreme weather patterns. The primary cause is increased greenhouse gas emissions from human activities such as burning fossil fuels, deforestation, and industrial processes. Carbon dioxide levels have reached unprecedented heights, leading to ocean acidification and ecosystem disruption. Scientists warn that without immediate action to reduce emissions and transition to renewable energy sources, the consequences could be catastrophic for future generations. International cooperation through agreements like the Paris Climate Accord aims to limit global warming to 1.5 degrees Celsius above pre-industrial levels.
            """
        elif not user_input:
            print("❌ No input provided. Skipping...")
            continue
        else:
            input_text = user_input
        
        # Get target length
        target_input = input(f"Target summary length (default: 200): ").strip()
        target_length = int(target_input) if target_input.isdigit() else 200
        
        # Prepare execution data
        execution_data = {
            "input_text": input_text.strip(),
            "target_length": target_length,
            "quality_threshold": 0.7
        }
        
        print(f"\n⚡ PROCESSING with {workflow_name}...")
        print(f"📊 Input: {len(input_text)} chars → Target: {target_length} chars")
        print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
        
        # Execute workflow
        try:
            result = await engine.run_workflow(graph_id, execution_data)
            
            print(f"\n🎯 RESULTS:")
            print(f"✅ Status: {result.status}")
            print(f"📝 Summary: {result.current_state.get('final_summary', 'No summary generated')}")
            print(f"📏 Length: {len(result.current_state.get('final_summary', ''))} characters")
            
            if 'quality_score' in result.current_state.data:
                print(f"🔍 Quality: {result.current_state.get('quality_score', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            import traceback
            traceback.print_exc()
        
        # Ask if user wants to continue
        continue_choice = input(f"\n🔄 Test another workflow? (y/n): ").strip().lower()
        if continue_choice != 'y':
            break
    
    print("\n🎉 Interactive test session completed!")

if __name__ == "__main__":
    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()