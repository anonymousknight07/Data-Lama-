import os
import requests
import time
import random
from typing import List, Dict, Optional
from app.utils import build_citation_list, format_superscripts
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-exp:free"

# Rate limiting configuration
RATE_LIMIT_DELAY = 2  # seconds between requests
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # exponential backoff multiplier

class RateLimitedClient:
    def __init__(self):
        self.last_request_time = 0
        self.request_count = 0
        
    def wait_if_needed(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last
            logger.info(f"Rate limiting: waiting {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1

# Global rate limiter instance
rate_limiter = RateLimitedClient()

def get_api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set. See .env file")
    return key

def call_openrouter(messages: List[Dict], max_retries: int = MAX_RETRIES) -> str:
    """
    Call OpenRouter API with rate limiting and retry logic
    """
    for attempt in range(max_retries):
        try:
            # Apply rate limiting
            rate_limiter.wait_if_needed()
            
            headers = {
                "Authorization": f"Bearer {get_api_key()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-domain.com",  # Add referer for better rate limits
                "X-Title": "Data Llama Business Analyst"  # Add title for identification
            }
            
            payload = {
                "model": MODEL,
                "messages": messages,
                "max_tokens": 2000,  # Limit response length to avoid timeouts
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            logger.info(f"Making OpenRouter request (attempt {attempt + 1}/{max_retries})")
            
            resp = requests.post(
                OPENROUTER_URL, 
                headers=headers, 
                json=payload, 
                timeout=60  # Increased timeout
            )
            
            # Handle different HTTP status codes
            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"].strip()
                logger.info(f"OpenRouter request successful")
                return content
            
            elif resp.status_code == 429:  # Rate limit exceeded
                retry_after = int(resp.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit (429). Retry after {retry_after} seconds")
                
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = min(retry_after, (BACKOFF_FACTOR ** attempt) * RATE_LIMIT_DELAY)
                    wait_time += random.uniform(0, 1)  # Add jitter
                    logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts")
            
            elif resp.status_code == 401:
                raise Exception("Invalid API key. Please check your OPENROUTER_API_KEY")
            
            elif resp.status_code == 402:
                raise Exception("Insufficient credits. Please add credits to your OpenRouter account")
            
            elif resp.status_code >= 500:
                logger.warning(f"Server error {resp.status_code}. Retrying...")
                if attempt < max_retries - 1:
                    time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                    continue
                else:
                    raise Exception(f"Server error {resp.status_code} after {max_retries} attempts")
            
            else:
                resp.raise_for_status()
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise Exception("Request timeout after multiple attempts")
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise Exception("Connection error after multiple attempts")
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Unexpected error: {e}. Retrying...")
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise e
    
    # If we get here, all attempts failed
    return generate_fallback_response(messages)

def generate_fallback_response(messages: List[Dict]) -> str:
    """Generate a fallback response when API calls fail"""
    user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
    
    # Extract the question from the user message
    if "Question:" in user_message:
        question = user_message.split("Question:")[1].split("\n")[0].strip()
    else:
        question = user_message[:100] + "..." if len(user_message) > 100 else user_message
    
    return f"""I apologize, but I'm currently experiencing high demand and cannot access the AI model to provide a comprehensive analysis of your question about {question}.

**What this means:**
- The OpenRouter API is currently rate-limited due to high usage
- This is a temporary issue that typically resolves within a few minutes

**What you can do:**
1. **Wait and retry**: Please try asking your question again in 2-3 minutes
2. **Check your API limits**: If you have a paid OpenRouter account, you may have reached your monthly limit
3. **Verify your API key**: Ensure your OPENROUTER_API_KEY is correctly set in your .env file

**Technical details:**
- Error: Rate limit exceeded (HTTP 429)
- This affects the AI analysis capability, but your application is working correctly
- Your sources are still being researched successfully

Please try your query again shortly. The system will automatically retry with proper rate limiting."""

def extract_assertions_from_source(text: str, url: str) -> List[Dict]:
    """Extract key assertions from source text with error handling"""
    prompt = (
        f"Excerpt: {text[:500]}...\n\n"
        f"Source URL: {url}\n\n"
        "Summarize the key assertion(s) from this excerpt in 1–2 sentences."
    )
    
    try:
        output = call_openrouter([
            {"role": "system", "content": "You are a fact extractor. Provide concise, accurate summaries."},
            {"role": "user", "content": prompt},
        ])
        return [{"assertion": output, "type": "note", "source": url}]
    except Exception as e:
        logger.warning(f"Failed to extract assertions for {url}: {e}")
        # Fallback: create assertion from the text directly
        summary = text[:200] + "..." if len(text) > 200 else text
        return [{"assertion": f"Key information from source: {summary}", "type": "note", "source": url}]

def synthesize_from_sources(question: str, sources: List[Dict]) -> Dict:
    """
    Synthesize answer from sources with comprehensive error handling
    """
    try:
        citations = build_citation_list(sources)
        
        # Create a more detailed context for the AI
        source_context = "\n\n".join([
            f"Source {i+1} ({src.get('title', 'Unknown')}): {src.get('text', src.get('summary', ''))[:500]}..."
            for i, src in enumerate(sources[:5])  # Limit to first 5 sources to avoid token limits
        ])
        
        user_text = (
            f"Question: {question}\n\n"
            f"Context from sources:\n{source_context}\n\n"
            "Based on the provided sources, answer the question clearly and professionally. "
            "Cite sources inline using [1], [2], etc. "
            "Provide a structured, comprehensive business analysis. "
            "Do NOT include a separate 'Sources' section at the end."
        )
        
        logger.info("Generating AI response for question synthesis")
        
        answer = call_openrouter([
            {"role": "system", "content": 
                "You are an expert business analyst providing professional insights. "
                "Structure your response clearly with headings and bullet points where appropriate. "
                "Cite sources using [1], [2] format inline. "
                "Focus on actionable insights and practical recommendations. "
                "Do NOT add a 'Sources' section - the frontend handles that."
            },
            {"role": "user", "content": user_text},
        ])
        
        # Format [1], [2], etc. into clickable superscripts
        formatted_answer = format_superscripts(answer, citations)
        
        return {
            "answer": formatted_answer, 
            "citations": citations,
            "source_count": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Error in synthesize_from_sources: {e}")
        
        # Provide a meaningful fallback response
        fallback_answer = f"""I apologize, but I'm currently unable to provide a comprehensive AI-generated analysis due to API limitations. However, I can share that your research query "{question}" has successfully retrieved {len(sources)} relevant sources.

**Sources Retrieved:**
{chr(10).join([f"• {src.get('title', 'Source')} - {src.get('url', 'N/A')}" for src in sources[:3]])}
{'• ...' if len(sources) > 3 else ''}

**Recommendation:** Please try your question again in a few minutes. The system will automatically retry with proper rate limiting and should provide a full analysis then.

**What's working:** 
- Source research and content extraction ✓
- Citation formatting ✓  
- Data retrieval ✓

**What's temporarily unavailable:**
- AI synthesis and analysis (due to rate limiting)"""
        
        citations = build_citation_list(sources)
        
        return {
            "answer": fallback_answer,
            "citations": citations,
            "source_count": len(sources),
            "error": "API_RATE_LIMITED"
        }