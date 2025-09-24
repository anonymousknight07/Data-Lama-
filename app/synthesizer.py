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

# Default model if none specified
DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"

# Available models configuration with your specified models
AVAILABLE_MODELS = {
    "x-ai/grok-4-fast:free": {
        "name": "Grok 4 Fast",
        "provider": "xAI",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Lightning-fast responses with xAI's latest model",
        "logo": "https://logo.clearbit.com/x.ai"
    },
    "deepseek/deepseek-chat-v3.1:free": {
        "name": "DeepSeek Chat v3.1",
        "provider": "DeepSeek",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Advanced reasoning and coding capabilities",
        "logo": "https://logo.clearbit.com/deepseek.com"
    },
    "deepseek/deepseek-chat-v3-0324:free": {
        "name": "DeepSeek Chat v3.0",
        "provider": "DeepSeek",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Efficient general-purpose AI model",
        "logo": "https://logo.clearbit.com/deepseek.com"
    },
    "microsoft/mai-ds-r1:free": {
        "name": "MAI-DS R1",
        "provider": "Microsoft",
        "max_tokens": 4096,
        "supports_streaming": True,
        "description": "Microsoft's advanced AI for data science",
        "logo": "https://logo.clearbit.com/microsoft.com"
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "name": "Llama 3.3 70B",
        "provider": "Meta",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Meta's powerful open-source model",
        "logo": "https://logo.clearbit.com/meta.com"
    },
    "google/gemini-2.0-flash-exp:free": {
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Google's latest experimental model",
        "logo": "https://logo.clearbit.com/google.com"
    },
    "openai/gpt-oss-20b:free": {
        "name": "GPT OSS 20B",
        "provider": "OpenAI",
        "max_tokens": 4096,
        "supports_streaming": True,
        "description": "Open-source variant from OpenAI",
        "logo": "https://logo.clearbit.com/openai.com"
    },
    "mistralai/mistral-small-3.2-24b-instruct:free": {
        "name": "Mistral Small 3.2",
        "provider": "Mistral AI",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Efficient and capable European AI",
        "logo": "https://logo.clearbit.com/mistral.ai"
    },
    "google/gemma-3-27b-it:free": {
        "name": "Gemma 3 27B",
        "provider": "Google",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Google's instruction-tuned model",
        "logo": "https://logo.clearbit.com/google.com"
    },
    "mistralai/mistral-7b-instruct:free": {
        "name": "Mistral 7B Instruct",
        "provider": "Mistral AI",
        "max_tokens": 8192,
        "supports_streaming": True,
        "description": "Compact but powerful AI model",
        "logo": "https://logo.clearbit.com/mistral.ai"
    }
}

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

def validate_model(model_id: str) -> str:
    """Validate and return a supported model ID"""
    if not model_id:
        logger.warning("No model specified, using default")
        return DEFAULT_MODEL
    
    if model_id not in AVAILABLE_MODELS:
        logger.warning(f"Model {model_id} not in available models, using default")
        return DEFAULT_MODEL
    
    return model_id

def get_model_config(model_id: str) -> Dict:
    """Get configuration for a specific model"""
    validated_model = validate_model(model_id)
    return AVAILABLE_MODELS.get(validated_model, AVAILABLE_MODELS[DEFAULT_MODEL])

def call_openrouter(messages: List[Dict], model_id: str = None, max_retries: int = MAX_RETRIES) -> str:
    """
    Call OpenRouter API with rate limiting and retry logic
    """
    # Validate and get model configuration
    validated_model = validate_model(model_id)
    model_config = get_model_config(validated_model)
    
    logger.info(f"Using model: {validated_model} ({model_config['name']} by {model_config['provider']})")
    
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
            
            # Configure payload based on model capabilities
            payload = {
                "model": validated_model,
                "messages": messages,
                "max_tokens": min(2000, model_config.get('max_tokens', 2000)),  # Respect model limits
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            # Add streaming if supported (for future enhancement)
            if model_config.get('supports_streaming', False):
                # payload["stream"] = False  # Keep disabled for now
                pass
            
            logger.info(f"Making OpenRouter request to {validated_model} (attempt {attempt + 1}/{max_retries})")
            
            resp = requests.post(
                OPENROUTER_URL, 
                headers=headers, 
                json=payload, 
                timeout=120  # Longer timeout for more complex models
            )
            
            # Handle different HTTP status codes
            if resp.status_code == 200:
                result = resp.json()
                
                # Check if we got a valid response
                if 'choices' not in result or not result['choices']:
                    raise Exception("Invalid response format from OpenRouter API")
                    
                content = result["choices"][0]["message"]["content"].strip()
                
                # Log usage info if available
                if 'usage' in result:
                    usage = result['usage']
                    logger.info(f"Token usage - Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)}")
                
                logger.info(f"OpenRouter request successful with {validated_model}")
                return content
            
            elif resp.status_code == 400:
                # Bad request - likely model-specific issue
                error_msg = "Bad request"
                try:
                    error_detail = resp.json().get('error', {}).get('message', '')
                    error_msg = f"Bad request: {error_detail}"
                except:
                    pass
                
                # If it's a model-specific error, try fallback to default
                if validated_model != DEFAULT_MODEL:
                    logger.warning(f"Model {validated_model} failed with 400 error, trying default model")
                    return call_openrouter(messages, DEFAULT_MODEL, max_retries - attempt)
                else:
                    raise Exception(error_msg)
            
            elif resp.status_code == 401:
                raise Exception("Invalid API key. Please check your OPENROUTER_API_KEY")
            
            elif resp.status_code == 402:
                raise Exception("Insufficient credits. Please add credits to your OpenRouter account")
            
            elif resp.status_code == 429:  # Rate limit exceeded
                retry_after = int(resp.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit (429) for {validated_model}. Retry after {retry_after} seconds")
                
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = min(retry_after, (BACKOFF_FACTOR ** attempt) * RATE_LIMIT_DELAY)
                    wait_time += random.uniform(0, 1)  # Add jitter
                    logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts with {validated_model}")
            
            elif resp.status_code >= 500:
                logger.warning(f"Server error {resp.status_code} for {validated_model}. Retrying...")
                if attempt < max_retries - 1:
                    time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                    continue
                else:
                    raise Exception(f"Server error {resp.status_code} after {max_retries} attempts with {validated_model}")
            
            else:
                resp.raise_for_status()
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout for {validated_model} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise Exception(f"Request timeout after multiple attempts with {validated_model}")
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error for {validated_model} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise Exception(f"Connection error after multiple attempts with {validated_model}")
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Unexpected error with {validated_model}: {e}. Retrying...")
                time.sleep((BACKOFF_FACTOR ** attempt) * 2)
                continue
            else:
                raise e
    
    # If we get here, all attempts failed
    return generate_fallback_response(messages, validated_model)

def generate_fallback_response(messages: List[Dict], model_id: str = None) -> str:
    """Generate a fallback response when API calls fail"""
    model_config = get_model_config(model_id)
    model_name = model_config['name']
    
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
    
    return f"""I apologize, but I'm currently experiencing high demand and cannot access {model_name} to provide a comprehensive analysis of your question about {question}.

**What this means:**
- The {model_config['provider']} model ({model_name}) is currently rate-limited due to high usage
- This is a temporary issue that typically resolves within a few minutes

**What you can do:**
1. **Try a different model**: Switch to another available model in the model selector
2. **Wait and retry**: Please try asking your question again in 2-3 minutes with {model_name}
3. **Check your API limits**: If you have a paid OpenRouter account, you may have reached your monthly limit
4. **Verify your API key**: Ensure your OPENROUTER_API_KEY is correctly set in your .env file

**Available alternatives:**
- Try Grok 4 Fast for lightning-fast responses
- Try DeepSeek Chat for advanced reasoning
- Try Gemini 2.0 Flash for experimental features

**Technical details:**
- Model: {model_id or 'Unknown'}
- Provider: {model_config['provider']}
- Error: Rate limit or server error
- Your application is working correctly, this affects only the AI analysis capability

Please try your query again with the same or different model shortly. The system will automatically retry with proper rate limiting."""

def extract_assertions_from_source(text: str, url: str, model_id: str = None) -> List[Dict]:
    """Extract key assertions from source text with error handling"""
    prompt = (
        f"Excerpt: {text[:500]}...\n\n"
        f"Source URL: {url}\n\n"
        "Summarize the key assertion(s) from this excerpt in 1-2 sentences."
    )
    
    try:
        output = call_openrouter([
            {"role": "system", "content": "You are a fact extractor. Provide concise, accurate summaries."},
            {"role": "user", "content": prompt},
        ], model_id)
        return [{"assertion": output, "type": "note", "source": url}]
    except Exception as e:
        logger.warning(f"Failed to extract assertions for {url} using {model_id}: {e}")
        # Fallback: create assertion from the text directly
        summary = text[:200] + "..." if len(text) > 200 else text
        return [{"assertion": f"Key information from source: {summary}", "type": "note", "source": url}]

def synthesize_from_sources(question: str, sources: List[Dict], model_id: str = None) -> Dict:
    """
    Synthesize answer from sources with comprehensive error handling and model selection
    """
    try:
        # Validate the model
        validated_model = validate_model(model_id)
        model_config = get_model_config(validated_model)
        model_name = model_config['name']
        
        logger.info(f"Using model: {validated_model} ({model_name}) for synthesis")
        
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
        
        logger.info(f"Generating AI response using {model_name} for question synthesis")
        
        # Customize system prompt based on model capabilities
        system_prompt = f"""You are an expert business analyst providing professional insights using {model_name}. 
Structure your response clearly with headings and bullet points where appropriate. 
Cite sources using [1], [2] format inline. 
Focus on actionable insights and practical recommendations. 
Do NOT add a 'Sources' section - the frontend handles that.
Leverage your model's strengths for high-quality analysis."""
        
        # Make the API call with the validated model
        answer = call_openrouter([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ], validated_model)  # Pass the validated model here
        
        # Format [1], [2], etc. into clickable superscripts
        formatted_answer = format_superscripts(answer, citations)
        
        return {
            "answer": formatted_answer, 
            "citations": citations,
            "source_count": len(sources),
            "model_used": model_name,
            "model_id": validated_model
        }
        
    except Exception as e:
        logger.error(f"Error in synthesize_from_sources with {model_id}: {e}")
        
        # Use the validated model for error handling
        validated_model = validate_model(model_id)
        model_config = get_model_config(validated_model)
        model_name = model_config['name']
        
        # Provide a meaningful fallback response
        fallback_answer = f"""I apologize, but I'm currently unable to provide a comprehensive AI-generated analysis using {model_name} due to API limitations. However, I can share that your research query "{question}" has successfully retrieved {len(sources)} relevant sources.

**Sources Retrieved:**
{chr(10).join([f"• {src.get('title', 'Source')} - {src.get('url', 'N/A')}" for src in sources[:3]])}
{'• ...' if len(sources) > 3 else ''}

**Recommendation:** 
1. **Try a different model**: Switch to another model using the model selector
2. **Wait and retry**: Try your question again in a few minutes with {model_name}

**Alternative models to try:**
- Grok 4 Fast for lightning-fast responses
- DeepSeek Chat for advanced reasoning
- Gemini 2.0 Flash for experimental features

**What's working:** 
- Source research and content extraction ✓
- Citation formatting ✓  
- Data retrieval ✓

**What's temporarily unavailable:**
- {model_name} synthesis and analysis (due to rate limiting or server issues)"""
        
        citations = build_citation_list(sources)
        
        return {
            "answer": fallback_answer,
            "citations": citations,
            "source_count": len(sources),
            "error": "API_RATE_LIMITED",
            "model_used": model_name,
            "model_id": validated_model,
            "suggested_alternatives": ["x-ai/grok-4-fast:free", "deepseek/deepseek-chat-v3.1:free", "google/gemini-2.0-flash-exp:free"]
        }

def get_available_models() -> Dict:
    """Return the list of available models for frontend"""
    return {
        "models": [
            {
                "id": model_id,
                "name": config["name"],
                "description": config.get("description", "High-quality AI model"),
                "provider": config["provider"],
                "icon": model_id.split("/")[0][0].upper(),  # First letter of provider
                "logo": config.get("logo", ""),
                "max_tokens": config.get("max_tokens", 4096),
                "supports_streaming": config.get("supports_streaming", False)
            }
            for model_id, config in AVAILABLE_MODELS.items()
        ],
        "default": DEFAULT_MODEL
    }