#!/usr/bin/env python3
"""
Quick WebSocket Test
"""
import asyncio
import json
import requests
import websockets

async def test_websocket_streaming():
    base_url = "http://localhost:8000"
    api_base = f"{base_url}/api/v1"
    
    print("🧪 Testing WebSocket Streaming Fix")
    print("=" * 40)
    
    # Check server
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Server health: {response.status_code}")
    except:
        print("❌ Server not running. Start with: python main.py")
        return
    
    # Get graph ID
    response = requests.get(f"{api_base}/graphs")
    graphs = response.json()['graphs']
    if not graphs:
        print("❌ No graphs available")
        return
    
    graph_id = graphs[0]['graph_id']
    print(f"📋 Using graph: {graph_id}")
    
    # Prepare test data
    test_text = """
    This is a test document for WebSocket streaming. We want to see the workflow 
    execute step by step with proper event streaming. The text should be long enough 
    to trigger multiple processing steps and demonstrate the asynchronous execution 
    capabilities of our workflow engine.
    """
    
    run_request = {
        "graph_id": graph_id,
        "initial_state": {
            "input_text": test_text.strip(),
            "target_length": 100
        }
    }
    
    # Start workflow
    print(f"\n🚀 Starting workflow...")
    response = requests.post(f"{api_base}/graph/run", json=run_request)
    
    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return
    
    run_data = response.json()
    run_id = run_data['run_id']
    print(f"✅ Started run: {run_id}")
    print(f"   Status: {run_data['status']}")
    
    # Connect to WebSocket
    websocket_url = f"ws://localhost:8000/api/v1/ws/{run_id}"
    print(f"\n🌐 Connecting to: {websocket_url}")
    
    try:
        async with websockets.connect(websocket_url) as ws:
            print("✅ WebSocket connected! Waiting for events...\n")
            
            events_count = 0
            timeout_count = 0
            max_timeout = 30  # 30 seconds max wait
            
            while timeout_count < max_timeout:
                try:
                    # Wait for message with 1 second timeout
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    event = json.loads(message)
                    
                    events_count += 1
                    event_type = event.get('event_type', 'unknown')
                    data = event.get('data', {})
                    
                    print(f"📨 [{events_count}] {event_type}")
                    
                    # Show relevant data based on event type
                    if event_type == "node_started":
                        print(f"   Node: {data.get('node_id')} ({data.get('tool')})")
                    elif event_type == "node_completed":
                        print(f"   Node: {data.get('node_id')} - Success")
                        result = data.get('result')
                        if isinstance(result, list):
                            print(f"   Result: {len(result)} items")
                        elif isinstance(result, str):
                            print(f"   Result: {len(result)} chars")
                    elif event_type == "workflow_completed":
                        print("🎉 Workflow completed!")
                        break
                    elif event_type == "workflow_failed":
                        print(f"💥 Workflow failed: {data.get('error')}")
                        break
                    
                    timeout_count = 0  # Reset timeout counter on successful event
                    
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count % 5 == 0:  # Print every 5 seconds
                        print(f"⏳ Waiting for events... ({timeout_count}s)")
                
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed")
                    break
            
            if timeout_count >= max_timeout:
                print("⚠️ Timeout reached, checking final status...")
            
            print(f"\n📊 Total events received: {events_count}")
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    
    # Check final status
    print(f"\n🔍 Checking final status...")
    response = requests.get(f"{api_base}/graph/state/{run_id}")
    
    if response.status_code == 200:
        status_data = response.json()
        print(f"✅ Final status: {status_data['status']}")
        print(f"   Nodes executed: {len(status_data['node_executions'])}")
        
        if 'final_summary' in status_data['current_state']:
            summary = status_data['current_state']['final_summary']
            print(f"📜 Summary: {summary[:100]}...")
    else:
        print(f"❌ Could not get final status: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_websocket_streaming())