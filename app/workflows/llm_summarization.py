import logging
from typing import Dict, List, Any
from ..core.workflow_engine import WorkflowEngine
from ..core.tools import tool_registry

logger = logging.getLogger(__name__)


def create_llm_summarization_workflow() -> Dict[str, Any]:
    """
    Create the LLM-powered summarization + refinement workflow definition.
    
    Workflow steps:
    1. Split text into chunks
    2. Generate LLM summaries for each chunk  
    3. Merge summaries into one
    4. LLM refine final summary
    5. Loop until summary meets quality criteria
    """
    
    workflow_definition = {
        "description": "LLM-Powered Text Summarization + Refinement Pipeline",
        "start_node": "split_text",
        "nodes": [
            {
                "id": "split_text",
                "tool": "split_text",
                "description": "Split input text into manageable chunks",
                "params": {
                    "text": "$state.input_text",
                    "chunk_size": 1500,  # Larger chunks for LLM
                    "overlap": 200
                }
            },
            {
                "id": "llm_generate_summaries",
                "tool": "process_chunks_llm", 
                "description": "Generate LLM summaries for all text chunks",
                "params": {
                    "chunks": "$state.split_text_result",
                    "max_length": 300
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
                "id": "llm_refine_summary",
                "tool": "llm_refine_summary",
                "description": "LLM refine and polish the merged summary",
                "params": {
                    "original_text": "$state.input_text",
                    "summary": "$state.merge_summaries_result",
                    "target_length": "$state.target_length"
                }
            },
            {
                "id": "quality_check",
                "tool": "llm_quality_assessment",
                "description": "Assess summary quality and determine next steps",
                "params": {
                    "original_text": "$state.input_text",
                    "summary": "$state.llm_refine_summary_result",
                    "target_length": "$state.target_length"
                }
            },
            {
                "id": "finish",
                "tool": "finalize_summary",
                "description": "Finalize summary",
                "params": {
                    "summary": "$state.llm_refine_summary_result"
                }
            }
        ],
        "edges": [
            {
                "from": "split_text",
                "to": "llm_generate_summaries"
            },
            {
                "from": "llm_generate_summaries", 
                "to": "merge_summaries"
            },
            {
                "from": "merge_summaries",
                "to": "llm_refine_summary"
            },
            {
                "from": "llm_refine_summary",
                "to": "quality_check"
            },
            {
                "from": "quality_check",
                "to": "llm_refine_summary",
                "condition": {
                    "type": "eq",
                    "key": "needs_refinement",
                    "value": True
                }
            },
            {
                "from": "quality_check",
                "to": "finish",
                "condition": {
                    "type": "eq",
                    "key": "needs_refinement", 
                    "value": False
                }
            }
        ]
    }
    
    return workflow_definition


# Register LLM-enhanced tools for the workflow
@tool_registry.tool("process_chunks_llm", "Process text chunks with LLM summaries", async_func=True)
async def process_chunks_llm(chunks: List[str], max_length: int = 300) -> Dict[str, List[str]]:
    """Process multiple chunks and generate LLM summaries with detailed logging"""
    print(f"\n🧠 LLM Chunk Processing Started...")
    print(f"📦 Processing {len(chunks)} text chunks")
    print(f"🎯 Target summary length per chunk: {max_length} characters")
    
    if not chunks:
        print("❌ No chunks to process")
        return {"chunk_summaries": []}
    
    chunk_summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"\n🔄 Processing chunk {i+1}/{len(chunks)}...")
        print(f"📏 Chunk size: {len(chunk)} characters")
        print(f"📝 Chunk preview: {chunk[:80]}...")
        
        if not chunk.strip():
            print("⚠️ Empty chunk, skipping...")
            continue
            
        # Use LLM summarization with fallback
        print(f"🤖 Calling hybrid summarization for chunk {i+1}...")
        summary = await tool_registry.execute("hybrid_summarize", text=chunk, max_length=max_length)
        chunk_summaries.append(summary)
        print(f"✅ Chunk {i+1} summarized: {len(summary)} chars")
    
    print(f"\n🎉 LLM Chunk Processing Complete!")
    print(f"📊 Generated {len(chunk_summaries)} chunk summaries")
    total_length = sum(len(s) for s in chunk_summaries)
    print(f"📏 Total summary length: {total_length} characters")
    
    return {"chunk_summaries": chunk_summaries}


@tool_registry.tool("llm_quality_assessment", "LLM-based quality assessment", async_func=True)
async def llm_quality_assessment(original_text: str, summary: str, target_length: int) -> Dict[str, Any]:
    """Assess summary quality using both LLM and rule-based metrics with detailed logging"""
    print(f"\n🔍 Quality Assessment Starting...")
    print(f"📄 Original text: {len(original_text)} characters")
    print(f"📝 Summary: {len(summary)} characters") 
    print(f"🎯 Target length: {target_length} characters")
    print(f"📊 Summary preview: {summary[:100]}...")
    
    if not summary:
        print("❌ Empty summary detected")
        return {
            "summary_length": 0,
            "quality_score": 0.0,
            "needs_refinement": True,
            "final_summary": "",
            "assessment": "Empty summary",
            "llm_assessment": "No summary to assess"
        }
    
    summary_length = len(summary)
    print(f"\n📐 Length Analysis:")
    print(f"   Current: {summary_length} chars")
    print(f"   Target: {target_length} chars")
    print(f"   Ratio: {summary_length/target_length:.2f}")
    
    # Rule-based quality score
    print(f"\n📏 Rule-based Quality Assessment...")
    rule_score = tool_registry._tools["calculate_summary_score"](original_text, summary)
    print(f"✅ Rule-based score: {rule_score:.2f}")
    
    # LLM-based quality assessment
    print(f"\n🤖 LLM Quality Assessment...")
    llm_assessment = ""
    llm_score = rule_score  # Default to rule score
    
    try:
        from ..core.llm_client import groq_client
        
        if groq_client.is_available():
            print("🔥 Using LLM for quality assessment...")
            assessment_prompt = f"""Please assess the quality of this summary on a scale of 0.0 to 1.0:

Original text (first 500 chars): {original_text[:500]}...
Summary: {summary}

Rate the summary quality (0.0-1.0) based on:
1. Accuracy and completeness
2. Clarity and readability  
3. Conciseness
4. Preservation of key information

Respond with just a number between 0.0 and 1.0, followed by a brief assessment."""

            completion = groq_client.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Current supported model
                messages=[{
                    "role": "user",
                    "content": assessment_prompt
                }],
                temperature=0.1,
                max_tokens=100
            )
            
            response = completion.choices[0].message.content.strip()
            print(f"🤖 LLM response: {response[:100]}...")
            
            # Extract score and assessment
            try:
                lines = response.split('\n')
                score_line = lines[0].strip()
                llm_score = float(score_line.split()[0])
                llm_assessment = '\n'.join(lines[1:]).strip() if len(lines) > 1 else response
                print(f"✅ LLM score extracted: {llm_score}")
            except:
                llm_assessment = response
                print(f"⚠️ Could not extract numeric score, using rule score")
        else:
            print("⚠️ LLM not available for quality assessment")
                
    except Exception as e:
        logger.warning(f"LLM quality assessment failed: {e}")
        print(f"❌ LLM assessment failed: {e}")
        llm_assessment = f"LLM assessment failed: {str(e)}"
    
    # Combined quality score (weighted average)
    combined_score = (rule_score * 0.3) + (llm_score * 0.7)
    print(f"\n📊 Quality Scores Summary:")
    print(f"   Rule-based: {rule_score:.2f}")
    print(f"   LLM-based: {llm_score:.2f}")
    print(f"   Combined: {combined_score:.2f}")
    
    # Determine if refinement is needed
    length_ok = summary_length <= target_length * 1.1  # 10% tolerance
    quality_ok = combined_score >= 0.7
    needs_refinement = not (length_ok and quality_ok)
    
    print(f"\n🔍 Quality Check Results:")
    print(f"   Length OK: {length_ok} (≤ {target_length * 1.1:.0f} chars)")
    print(f"   Quality OK: {quality_ok} (≥ 0.7 score)")
    print(f"   Needs refinement: {needs_refinement}")
    
    assessment = {
        "summary_length": summary_length,
        "quality_score": round(combined_score, 2),
        "rule_score": round(rule_score, 2),
        "llm_score": round(llm_score, 2),
        "needs_refinement": needs_refinement,
        "final_summary": summary if not needs_refinement else summary,  # Always include summary
        "target_length": target_length,
        "llm_assessment": llm_assessment
    }
    
    if needs_refinement:
        reasons = []
        if not length_ok:
            reasons.append(f"too long ({summary_length} > {target_length})")
        if not quality_ok:
            reasons.append(f"low quality ({combined_score})")
        assessment["assessment"] = f"Needs refinement: {', '.join(reasons)}"
    else:
        assessment["assessment"] = f"Summary meets criteria: length={summary_length}, quality={combined_score}"
    
    return assessment


# Create sample workflow function for LLM testing
def create_sample_llm_summarization_run() -> Dict[str, Any]:
    """Create a sample LLM summarization workflow run with test data"""
    
    sample_text = """
    Artificial Intelligence has revolutionized numerous industries and continues to shape our technological landscape. 
    Machine learning algorithms can now process vast amounts of data to identify patterns and make predictions with 
    unprecedented accuracy. Deep learning, a subset of machine learning, uses artificial neural networks inspired by 
    the human brain to solve complex problems in image recognition, natural language processing, and autonomous systems.
    
    The applications of AI span across healthcare, where it assists in medical diagnosis and drug discovery; finance, 
    where it enables algorithmic trading and fraud detection; transportation, through autonomous vehicles and traffic 
    optimization; and entertainment, via personalized content recommendations and computer graphics. As AI continues 
    to advance, researchers are exploring areas like quantum computing integration, explainable AI, and artificial 
    general intelligence.
    
    However, the rapid development of AI also raises important ethical considerations including job displacement, 
    privacy concerns, algorithmic bias, and the need for responsible AI governance. Organizations worldwide are 
    working to establish frameworks for ethical AI development that balance innovation with social responsibility. 
    The future of AI promises even more transformative applications while requiring careful consideration of its 
    societal impact.
    """
    
    return {
        "input_text": sample_text.strip(),
        "target_length": 250,
        "chunk_size": 800,
        "overlap": 100
    }


# Workflow registration helper
def register_llm_summarization_workflow(engine: WorkflowEngine) -> str:
    """Register the LLM summarization workflow with the engine"""
    definition = create_llm_summarization_workflow()
    graph_id = engine.create_graph(definition)
    return graph_id