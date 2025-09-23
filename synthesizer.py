import os
import requests
import time
from app.utils import build_citation_list, format_superscripts, chunk_text
import logging

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-nano-9b-v2:free"

def get_api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set. See .env file")
    return key

def call_openrouter(messages, max_retries=3):
    """
    Call OpenRouter API with retry logic
    """
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL, 
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            logger.warning(f"API call attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    
    raise Exception("Max retries exceeded")

def extract_assertions_from_source(text: str, url: str):
    """
    Extract key insights from source content
    """
    try:
        # Truncate text if too long
        excerpt = text[:1000] if len(text) > 1000 else text
        
        prompt = (
            f"Analyze this content and extract 2-3 key business insights:\n\n"
            f"Content: {excerpt}\n\n"
            f"Source: {url}\n\n"
            f"Provide concise, actionable insights that would be valuable for business analysis."
        )
        
        output = call_openrouter([
            {"role": "system", "content": "You are an expert business analyst. Extract the most valuable insights from content."},
            {"role": "user", "content": prompt},
        ])
        
        return [{"assertion": output, "type": "insight", "source": url}]
    except Exception as e:
        logger.error(f"Failed to extract insights from {url}: {e}")
        # Fallback to first 200 characters
        fallback_text = text[:200] + "..." if len(text) > 200 else text
        return [{"assertion": fallback_text, "type": "fallback", "source": url}]

def create_enhanced_citations(sources: list) -> list:
    """
    Use the existing build_citation_list function
    """
    return build_citation_list(sources)

def synthesize_from_sources(question: str, sources: list) -> dict:
    """
    Enhanced synthesis using existing utilities
    """
    try:
        # Prepare source content with chunking for large texts
        source_content = []
        for i, source in enumerate(sources, 1):
            content = source.get('text', '')
            title = source.get('title', f'Source {i}')
            url = source.get('url', '#')
            is_synthetic = source.get('synthetic', False)
            
            # Use chunking for very long content
            if len(content) > 2000:
                chunks = chunk_text(content, max_chars=2000)
                content = chunks[0] + "..." if chunks else content[:2000] + "..."
            
            source_type = " (AI Generated)" if is_synthetic else ""
            source_content.append(f"[{i}] {title}{source_type}\nURL: {url}\nContent: {content}\n")
        
        # Create synthesis prompt
        user_text = (
            f"Question: {question}\n\n"
            f"Sources:\n" + "\n".join(source_content) + "\n\n"
            f"Instructions:\n"
            f"1. Provide a comprehensive analysis based on the sources\n"
            f"2. Use markdown formatting for better readability\n"
            f"3. Include tables when comparing different approaches or models\n"
            f"4. Reference sources using [1], [2], etc. notation in your text\n"
            f"5. Focus on actionable insights for business professionals\n"
            f"6. If sources discuss different methodologies, create comparison tables\n"
            f"7. Structure your response with clear headings and sections\n"
            f"8. Always cite sources by including [1], [2] etc. after relevant statements"
        )
        
        system_prompt = (
            "You are an expert business analyst and consultant. "
            "Provide clear, structured, and actionable analysis. "
            "Use markdown formatting including headers, tables, and lists. "
            "When comparing different approaches, always use tables for clarity. "
            "IMPORTANT: Always cite sources using [1], [2], etc. notation after relevant statements. "
            "Maintain professional tone and focus on practical business insights."
        )
        
        answer = call_openrouter([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ])
        
        # Create citations using existing utility
        citations = build_citation_list(sources)
        
        # Format superscripts in the answer
        formatted_answer = format_superscripts(answer, citations)
        
        return {"answer": formatted_answer, "citations": citations}
        
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        
        # Fallback response
        fallback_answer = (
            f"# Analysis: {question}\n\n"
            f"I encountered some technical difficulties while processing your request. "
            f"However, based on general knowledge, here are some key insights:\n\n"
            f"## Key Points\n\n"
            f"- This topic involves multiple approaches and methodologies\n"
            f"- Different frameworks offer various advantages and trade-offs\n"
            f"- The best approach depends on your specific context and goals\n\n"
            f"## Recommendations\n\n"
            f"1. **Evaluate your specific needs** - Consider your team size, resources, and objectives\n"
            f"2. **Start with proven frameworks** - Begin with well-established methodologies\n"
            f"3. **Iterate and adapt** - Adjust your approach based on results and feedback\n\n"
            f"For more detailed analysis, please try rephrasing your question or breaking it into smaller parts."
        )
        
        fallback_citations = [f"[1] Fallback Analysis — generated://fallback"]
        
        return {
            "answer": fallback_answer,
            "citations": fallback_citations
        }