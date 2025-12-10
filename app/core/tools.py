from typing import Dict, Callable, Any, List, Optional
import asyncio
import logging
from functools import wraps

# Import LLM client
from .llm_client import groq_client

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for workflow tools/functions"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(
        self, 
        name: str, 
        func: Callable, 
        description: str = "", 
        async_func: bool = False
    ) -> None:
        """Register a tool function"""
        self._tools[name] = func
        self._tool_metadata[name] = {
            "description": description,
            "async": async_func,
            "registered_at": asyncio.get_event_loop().time()
        }
        logger.info(f"Registered tool: {name}")
    
    def tool(self, name: str, description: str = "", async_func: bool = False):
        """Decorator to register a tool"""
        def decorator(func: Callable):
            self.register(name, func, description, async_func)
            return func
        return decorator
    
    async def execute(self, name: str, *args, **kwargs) -> Any:
        """Execute a tool by name"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        
        tool = self._tools[name]
        metadata = self._tool_metadata[name]
        
        try:
            if metadata.get("async", False):
                result = await tool(*args, **kwargs)
            else:
                result = tool(*args, **kwargs)
            
            logger.info(f"Tool '{name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {str(e)}")
            raise
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools with metadata"""
        return {
            name: {
                **metadata,
                "available": True
            }
            for name, metadata in self._tool_metadata.items()
        }
    
    def has_tool(self, name: str) -> bool:
        """Check if tool exists"""
        return name in self._tools


# Global tool registry instance
tool_registry = ToolRegistry()


# Summarization workflow tools
@tool_registry.tool("split_text", "Split text into manageable chunks")
def split_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        if end > text_len:
            end = text_len
        
        chunk = text[start:end]
        
        # Try to end at word boundary
        if end < text_len and chunk[-1] != ' ':
            last_space = chunk.rfind(' ')
            if last_space > chunk_size // 2:  # Only if we find a reasonable space
                chunk = chunk[:last_space]
                end = start + last_space
        
        chunks.append(chunk.strip())
        
        if end >= text_len:
            break
            
        start = end - overlap
    
    return [chunk for chunk in chunks if chunk]


@tool_registry.tool("generate_summary", "Generate summary for a text chunk", async_func=True)
async def generate_summary(text: str, max_length: int = 200) -> str:
    """Generate a simple extractive summary"""
    # Simulate async operation
    await asyncio.sleep(0.1)
    
    if not text:
        return ""
    
    sentences = text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return text[:max_length]
    
    # Simple extractive summary - take first few sentences
    summary_sentences = []
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) + 1 > max_length:
            break
        summary_sentences.append(sentence)
        current_length += len(sentence) + 1
    
    if not summary_sentences:
        return text[:max_length]
    
    return '. '.join(summary_sentences) + '.'


@tool_registry.tool("merge_summaries", "Merge multiple summaries into one")
def merge_summaries(summaries: List[str]) -> str:
    """Merge multiple summaries with detailed logging"""
    print(f"\n🔗 Merging Summaries Process...")
    print(f"📊 Input: {len(summaries)} summaries to merge")
    
    if not summaries:
        print("❌ No summaries to merge")
        return ""
    
    # Show each summary being merged
    for i, summary in enumerate(summaries, 1):
        print(f"📄 Summary {i} ({len(summary)} chars): {summary[:60]}...")
    
    # Remove duplicates while preserving order
    unique_summaries = []
    seen = set()
    
    for summary in summaries:
        summary = summary.strip()
        if summary and summary not in seen:
            unique_summaries.append(summary)
            seen.add(summary)
    
    if len(unique_summaries) < len(summaries):
        print(f"🔄 Removed {len(summaries) - len(unique_summaries)} duplicate summaries")
    
    merged = ' '.join(unique_summaries)
    print(f"✅ Merged result ({len(merged)} chars): {merged[:100]}...")
    
    return merged


@tool_registry.tool("refine_summary", "Refine and polish the final summary", async_func=True)
async def refine_summary(summary: str, target_length: int = 500) -> str:
    """Refine the summary to meet target length"""
    # Simulate async operation
    await asyncio.sleep(0.1)
    
    if not summary:
        return ""
    
    # If summary is already within target length, return as is
    if len(summary) <= target_length:
        return summary
    
    # Simple refinement - truncate at sentence boundary
    sentences = summary.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    refined_sentences = []
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) + 1 > target_length:
            break
        refined_sentences.append(sentence)
        current_length += len(sentence) + 1
    
    if not refined_sentences:
        return summary[:target_length]
    
    return '. '.join(refined_sentences) + '.'


@tool_registry.tool("calculate_summary_score", "Calculate quality score for summary")
def calculate_summary_score(original_text: str, summary: str) -> float:
    """Calculate a simple quality score for the summary"""
    if not original_text or not summary:
        return 0.0
    
    # Simple scoring based on compression ratio and content preservation
    compression_ratio = len(summary) / len(original_text)
    
    # Check for key terms preservation (simple word overlap)
    original_words = set(original_text.lower().split())
    summary_words = set(summary.lower().split())
    
    if not original_words:
        return 0.0
    
    word_overlap = len(original_words.intersection(summary_words)) / len(original_words)
    
    # Score combines compression efficiency and content preservation
    score = (word_overlap * 0.7) + (min(1.0, 1.0 - compression_ratio) * 0.3)
    
    return round(score, 2)


# LLM-Powered Tools using Groq
@tool_registry.tool("llm_summarize", "Generate summary using Groq LLM", async_func=True)
async def llm_summarize(text: str, max_length: int = 200) -> str:
    """Generate summary using Groq LLM with fallback to rule-based"""
    if not text:
        return ""
    
    try:
        # Try LLM first
        if groq_client.is_available():
            return await groq_client.summarize_text(text, max_length)
        else:
            logger.warning("Groq not available, falling back to rule-based summarization")
            # Fallback to original rule-based method
            return await generate_summary(text, max_length)
            
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}, falling back to rule-based")
        # Fallback to original method on any error
        return await generate_summary(text, max_length)


@tool_registry.tool("llm_summarize_streaming", "Generate summary using Groq LLM with streaming", async_func=True)
async def llm_summarize_streaming(
    text: str, 
    max_length: int = 200, 
    event_emitter: Optional[callable] = None
) -> str:
    """Generate summary using Groq LLM with streaming updates"""
    if not text:
        return ""
    
    try:
        if groq_client.is_available():
            # Define callback for streaming updates
            async def streaming_callback(event_type: str, data: Dict[str, Any]):
                if event_emitter:
                    await event_emitter(event_type, data)
            
            return await groq_client.summarize_text_streaming(
                text, 
                max_length, 
                callback=streaming_callback
            )
        else:
            logger.warning("Groq not available, falling back to rule-based summarization")
            return await generate_summary(text, max_length)
            
    except Exception as e:
        logger.error(f"LLM streaming summarization failed: {e}, falling back to rule-based")
        return await generate_summary(text, max_length)


@tool_registry.tool("llm_refine_summary", "Refine summary using Groq LLM", async_func=True)
async def llm_refine_summary(
    original_text: str,
    summary: str, 
    target_length: int = 200
) -> str:
    """Refine summary using Groq LLM with fallback"""
    if not summary:
        return ""
    
    try:
        if groq_client.is_available():
            return await groq_client.refine_summary(original_text, summary, target_length)
        else:
            logger.warning("Groq not available, falling back to rule-based refinement")
            return await refine_summary(summary, target_length)
            
    except Exception as e:
        logger.error(f"LLM refinement failed: {e}, falling back to rule-based")
        return await refine_summary(summary, target_length)


@tool_registry.tool("hybrid_summarize", "Smart summarization with LLM and fallback", async_func=True)
async def hybrid_summarize(text: str, max_length: int = 200, prefer_llm: bool = True) -> str:
    """Hybrid tool that uses LLM when available, rule-based as fallback with detailed logging"""
    if not text:
        return ""
    
    print(f"\n🤖 Hybrid Summarization Starting...")
    print(f"📝 Input length: {len(text)} characters")
    print(f"🎯 Target length: {max_length} characters")
    print(f"📄 Text preview: {text[:100]}...")
    
    if prefer_llm and groq_client.is_available():
        try:
            print("🔥 Using Groq LLM for intelligent summarization...")
            result = await groq_client.summarize_text(text, max_length)
            print(f"✅ LLM Summary generated ({len(result)} chars): {result[:80]}...")
            return result
        except Exception as e:
            print(f"❌ LLM failed: {e}")
            print("🔄 Falling back to rule-based summarization...")
    else:
        print("⚠️ LLM not available, using rule-based summarization...")
    
    result = await generate_summary(text, max_length)
    print(f"✅ Rule-based summary generated ({len(result)} chars): {result[:80]}...")
    return result


@tool_registry.tool("finalize_summary", "Finalize the workflow summary")
def finalize_summary(summary: str = "", **kwargs) -> Dict[str, Any]:
    """Finalize the summary by setting it as the final result with logging"""
    print(f"\n🏁 Finalizing Summary...")
    print(f"📝 Input summary ({len(summary)} chars): {summary[:100]}...")
    
    final_summary = summary.strip() if summary else "No summary generated"
    
    print(f"✅ Final summary set: {final_summary[:100]}...")
    print(f"📏 Final length: {len(final_summary)} characters")
    
    result = {
        "final_summary": final_summary,
        "summary_length": len(final_summary),
        "status": "completed"
    }
    
    print(f"🎉 Finalization complete!")
    return result