from typing import Dict, List, Any
from ..core.workflow_engine import WorkflowEngine
from ..core.tools import tool_registry


def create_summarization_workflow() -> Dict[str, Any]:
    """
    Create the summarization + refinement workflow definition.
    
    Workflow steps:
    1. Split text into chunks
    2. Generate summaries for each chunk  
    3. Merge summaries into one
    4. Refine final summary
    5. Loop until summary length is under target limit
    """
    
    workflow_definition = {
        "description": "Text Summarization + Refinement Pipeline",
        "start_node": "split_text",
        "nodes": [
            {
                "id": "split_text",
                "tool": "split_text",
                "description": "Split input text into manageable chunks",
                "params": {
                    "text": "$state.input_text",
                    "chunk_size": 1000,
                    "overlap": 100
                }
            },
            {
                "id": "generate_summaries",
                "tool": "process_chunks", 
                "description": "Generate summaries for all text chunks",
                "params": {
                    "chunks": "$state.split_text_result",
                    "max_length": 200
                }
            },
            {
                "id": "merge_summaries",
                "tool": "merge_summaries",
                "description": "Merge individual summaries into one",
                "params": {
                    "summaries": "$state.chunk_summaries"
                }
            },
            {
                "id": "refine_summary",
                "tool": "refine_summary",
                "description": "Refine and polish the merged summary",
                "params": {
                    "summary": "$state.merge_summaries_result",
                    "target_length": "$state.target_length"
                }
            },
            {
                "id": "quality_check",
                "tool": "quality_assessment",
                "description": "Check if summary meets quality criteria",
                "params": {
                    "original_text": "$state.input_text",
                    "summary": "$state.refine_summary_result",
                    "target_length": "$state.target_length"
                }
            }
        ],
        "edges": [
            {
                "from": "split_text",
                "to": "generate_summaries"
            },
            {
                "from": "generate_summaries", 
                "to": "merge_summaries"
            },
            {
                "from": "merge_summaries",
                "to": "refine_summary"
            },
            {
                "from": "refine_summary",
                "to": "quality_check"
            },
            {
                "from": "quality_check",
                "to": "refine_summary",
                "condition": {
                    "type": "gt",
                    "key": "summary_length",
                    "value": 300
                }
            }
        ]
    }
    
    return workflow_definition


# Register additional tools for the summarization workflow
@tool_registry.tool("process_chunks", "Process text chunks to generate summaries", async_func=True)
async def process_chunks(chunks: List[str], max_length: int = 200) -> Dict[str, List[str]]:
    """Process multiple chunks and generate summaries"""
    if not chunks:
        return {"chunk_summaries": []}
    
    chunk_summaries = []
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
            
        # Use the existing generate_summary tool
        summary = await tool_registry.execute("generate_summary", text=chunk, max_length=max_length)
        chunk_summaries.append(summary)
    
    return {"chunk_summaries": chunk_summaries}


@tool_registry.tool("quality_assessment", "Assess summary quality and determine next steps")
def quality_assessment(original_text: str, summary: str, target_length: int) -> Dict[str, Any]:
    """Assess summary quality and determine if refinement is needed"""
    if not summary:
        return {
            "summary_length": 0,
            "quality_score": 0.0,
            "needs_refinement": True,
            "final_summary": "",
            "assessment": "Empty summary"
        }
    
    summary_length = len(summary)
    quality_score = tool_registry._tools["calculate_summary_score"](original_text, summary)
    
    # Determine if refinement is needed
    needs_refinement = summary_length > target_length and quality_score < 0.8
    
    assessment = {
        "summary_length": summary_length,
        "quality_score": quality_score,
        "needs_refinement": needs_refinement,
        "final_summary": summary if not needs_refinement else "",
        "target_length": target_length
    }
    
    if needs_refinement:
        assessment["assessment"] = f"Summary too long ({summary_length} > {target_length}) or low quality ({quality_score})"
    else:
        assessment["assessment"] = f"Summary meets criteria: length={summary_length}, quality={quality_score}"
    
    return assessment


# Create sample workflow function for easy testing
def create_sample_summarization_run() -> Dict[str, Any]:
    """Create a sample summarization workflow run with test data"""
    
    sample_text = """
    Artificial Intelligence (AI) refers to the simulation of human intelligence in machines 
    that are programmed to think and learn like humans. The term may also be applied to any 
    machine that exhibits traits associated with a human mind such as learning and 
    problem-solving. The ideal characteristic of artificial intelligence is its ability to 
    rationalize and take actions that have the best chance of achieving a specific goal.
    
    Machine Learning is a subset of AI that provides systems the ability to automatically 
    learn and improve from experience without being explicitly programmed. Machine learning 
    focuses on the development of computer programs that can access data and use it to learn 
    for themselves. The process of learning begins with observations or data, such as examples, 
    direct experience, or instruction, in order to look for patterns in data and make better 
    decisions in the future based on the examples that we provide.
    
    Deep Learning is a subset of machine learning in artificial intelligence that has networks 
    capable of learning unsupervised from data that is unstructured or unlabeled. Also known 
    as deep neural learning or deep neural network, it is inspired by the structure and 
    function of the brain, specifically the neural network. Deep learning algorithms attempt 
    to draw similar conclusions as humans would by continually analyzing data with a logical 
    structure. To achieve this, deep learning applications use a layered structure of 
    algorithms called an artificial neural network.
    """
    
    return {
        "input_text": sample_text.strip(),
        "target_length": 300,
        "chunk_size": 500,
        "overlap": 50
    }


# Workflow registration helper
def register_summarization_workflow(engine: WorkflowEngine) -> str:
    """Register the summarization workflow with the engine"""
    definition = create_summarization_workflow()
    graph_id = engine.create_graph(definition)
    return graph_id