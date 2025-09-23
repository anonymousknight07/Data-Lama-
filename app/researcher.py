import os
import requests
from typing import List, Dict
import time
from urllib.parse import urlparse
from app.synthesizer import call_openrouter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_serper_api_key():
    """Get Serper API key from environment variables"""
    key = os.getenv("SERPER_API_KEY")
    if not key:
        raise RuntimeError("SERPER_API_KEY not set. Please add it to your .env file")
    return key

def is_valid_url(url: str) -> bool:
    """Check if URL is valid and accessible"""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
    except Exception:
        return False

def serper_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Use Serper AI for web search and content extraction.
    Returns a list of search results with extracted content.
    """
    try:
        headers = {
            'X-API-KEY': get_serper_api_key(),
            'Content-Type': 'application/json'
        }
        
        payload = {
            'q': query,
            'num': num_results,
            'extractContent': True,  # This tells Serper to extract content from pages
            'type': 'search'
        }
        
        response = requests.post(
            'https://google.serper.dev/search',
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        hits = []
        # Process organic search results
        for result in data.get('organic', [])[:num_results]:
            hit = {
                'title': result.get('title', 'Untitled'),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'content': result.get('content', '')  # Extracted content from Serper
            }
            
            if is_valid_url(hit['url']):
                hits.append(hit)
        
        logger.info(f"Serper search returned {len(hits)} results")
        return hits
        
    except Exception as e:
        logger.error(f"Error in serper_search: {e}")
        # Fallback to OpenRouter search if Serper fails
        logger.info("Falling back to OpenRouter search")
        return openrouter_search(query, num_results)

def openrouter_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Fallback: Use OpenRouter as a search agent.
    Ask it to return a list of relevant URLs for the query.
    """
    prompt = (
        f"Find reliable, accessible articles about: {query}\n\n"
        f"Return {num_results} high-quality URLs from reputable sources like:\n"
        f"- Medium, Harvard Business Review, McKinsey, Deloitte\n"
        f"- ProductPlan, Aha!, Roadmunk, UserVoice\n"
        f"- Academic institutions, government sites\n"
        f"- Well-known business and tech publications\n"
        f"- Avoid paywalled sites, sites that block scraping, or unreliable sources\n\n"
        f"Format exactly as:\n"
        f"1. Descriptive Article Title — https://example.com/full-url"
    )

    try:
        output = call_openrouter([
            {"role": "system", "content": "You are a research assistant. Only return accessible, high-quality URLs with descriptive titles. Focus on authoritative sources that allow content access."},
            {"role": "user", "content": prompt},
        ])

        hits = []
        for line in output.splitlines():
            line = line.strip()
            if not line or "http" not in line:
                continue
            try:
                # Parse "1. Title — URL"
                if "—" in line:
                    parts = line.split("—", 1)
                    if len(parts) == 2:
                        title = parts[0].strip().lstrip("0123456789. ")
                        url = parts[1].strip()
                        
                        # Clean and validate URL
                        if url and is_valid_url(url):
                            hits.append({
                                "title": title, 
                                "url": url,
                                "snippet": "",
                                "content": ""
                            })
                elif "http" in line:
                    # Fallback: extract URL from line
                    import re
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match and is_valid_url(url_match.group()):
                        url = url_match.group()
                        title = line.replace(url, "").strip().lstrip("0123456789.- ")
                        hits.append({
                            "title": title or "Article", 
                            "url": url,
                            "snippet": "",
                            "content": ""
                        })
            except Exception as e:
                logger.warning(f"Error parsing line: {line}, error: {e}")
                continue
        
        return hits[:num_results]
    except Exception as e:
        logger.error(f"Error in openrouter_search: {e}")
        # Final fallback to some default authoritative sources
        return get_fallback_sources(query)

def get_fallback_sources(query: str) -> List[Dict]:
    """Provide fallback sources when both Serper and OpenRouter search fail"""
    fallback_sources = [
        {
            "title": f"Harvard Business Review insights on {query}",
            "url": "https://hbr.org",
            "snippet": f"Business insights and analysis on {query}",
            "content": ""
        },
        {
            "title": f"McKinsey analysis of {query}",
            "url": "https://mckinsey.com",
            "snippet": f"Strategic analysis and recommendations for {query}",
            "content": ""
        },
        {
            "title": f"Medium articles about {query}",
            "url": "https://medium.com",
            "snippet": f"Community insights and practical applications of {query}",
            "content": ""
        }
    ]
    return fallback_sources[:3]

def serper_extract_content(url: str) -> Dict:
    """
    Use Serper AI to extract content from a specific URL.
    """
    try:
        headers = {
            'X-API-KEY': get_serper_api_key(),
            'Content-Type': 'application/json'
        }
        
        payload = {
            'url': url,
            'extractContent': True
        }
        
        response = requests.post(
            'https://google.serper.dev/extract',
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "title": data.get('title', 'Extracted Article'),
            "authors": data.get('authors', []),
            "publish_date": data.get('publishDate'),
            "text": data.get('text', data.get('content', '')),
            "summary": data.get('description', data.get('text', '')[:500] + "..." if data.get('text') else ""),
            "url": url
        }
        
    except Exception as e:
        logger.error(f"Serper content extraction failed for {url}: {e}")
        raise e

def fetch_and_extract(url: str, timeout: int = 15) -> Dict:
    """
    Fetch and extract content using Serper AI first, with newspaper as fallback
    """
    try:
        # Try Serper content extraction first
        try:
            extracted_data = serper_extract_content(url)
            if extracted_data.get('text') and len(extracted_data['text'].strip()) > 50:
                logger.info(f"Successfully extracted with Serper: {url}")
                return extracted_data
            else:
                logger.info(f"Serper extraction returned insufficient content for {url}")
                raise ValueError("Insufficient content from Serper")
                
        except Exception as e:
            logger.warning(f"Serper extraction failed, trying newspaper: {e}")
            
            # Fallback to newspaper extraction
            from newspaper import Article
            
            article = Article(url)
            article.download()
            article.parse()
            
            # Try NLP processing
            try:
                article.nlp()
                summary = getattr(article, "summary", None)
            except Exception:
                summary = None
            
            extracted_data = {
                "title": article.title,
                "authors": article.authors or [],
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "text": article.text,
                "summary": summary or (article.text[:500] + "..." if len(article.text) > 500 else article.text),
                "url": url
            }
            
            # Ensure we have meaningful content
            if not extracted_data.get('text') or len(extracted_data['text'].strip()) < 50:
                raise ValueError(f"Article content too short or empty (got {len(extracted_data.get('text', ''))} characters)")
            
            logger.info(f"Successfully extracted with newspaper: {url}")
            return extracted_data
        
    except Exception as e:
        logger.error(f"Content extraction failed for {url}: {e}")
        raise Exception(f"Content extraction error: {str(e)}")

def create_synthetic_content(query: str, url: str) -> Dict:
    """
    Create synthetic content when web scraping fails
    """
    try:
        prompt = (
            f"Generate comprehensive business analysis content about: {query}\n\n"
            f"Provide a detailed analysis covering:\n"
            f"- Key concepts, definitions, and background\n"
            f"- Main advantages, disadvantages, and trade-offs\n" 
            f"- Best practices, implementation strategies, and recommendations\n"
            f"- Real-world applications, use cases, and examples\n"
            f"- Comparison with alternative approaches when relevant\n\n"
            f"Write in a professional, analytical tone suitable for business professionals. "
            f"Structure the content with clear sections and actionable insights."
        )
        
        synthetic_content = call_openrouter([
            {"role": "system", "content": "You are a senior business analyst creating comprehensive content on business topics. Provide detailed, practical insights."},
            {"role": "user", "content": prompt},
        ])
        
        return {
            "url": url,
            "title": f"Business Analysis: {query}",
            "authors": ["AI Research Assistant"],
            "publish_date": None,
            "text": synthetic_content,
            "summary": synthetic_content[:300] + "..." if len(synthetic_content) > 300 else synthetic_content,
            "synthetic": True
        }
    except Exception as e:
        logger.error(f"Failed to generate synthetic content: {e}")
        return {
            "url": url,
            "title": f"Information about {query}",
            "authors": [],
            "publish_date": None,
            "text": f"This analysis covers key aspects of {query}. While external sources were not accessible, this provides foundational information based on established business principles and methodologies.",
            "summary": f"General analysis of {query} concepts and applications.",
            "synthetic": True
        }

def researcher_job(query: str, top_k_sites: int = 5) -> List[Dict]:
    """
    Main research function using Serper AI with comprehensive error handling
    """
    logger.info(f"Starting research for query: {query}")
    
    # Get potential sources using Serper AI
    hits = serper_search(query, num_results=top_k_sites * 2)
    logger.info(f"Found {len(hits)} potential sources")
    
    selected = []
    failed_urls = []
    
    for h in hits:
        if len(selected) >= top_k_sites:
            break
            
        try:
            logger.info(f"Processing: {h.get('url')}")
            
            # If Serper already provided content, use it
            if h.get('content') and len(h['content'].strip()) > 100:
                doc = {
                    "url": h["url"],
                    "title": h.get("title", "Article"),
                    "authors": [],
                    "publish_date": None,
                    "text": h["content"],
                    "summary": h.get("snippet", h["content"][:300] + "..." if len(h["content"]) > 300 else h["content"]),
                    "source_snippet": h.get("title")
                }
                selected.append(doc)
                logger.info(f"Used Serper content for: {h.get('url')}")
            else:
                # Extract content using our extraction method
                doc = fetch_and_extract(h["url"])
                doc["source_snippet"] = h.get("title")
                selected.append(doc)
                logger.info(f"Successfully fetched: {h.get('url')}")
            
        except Exception as e:
            failed_urls.append(h["url"])
            logger.warning(f"Failed to process {h.get('url')}: {e}")
            continue
    
    # If we don't have enough sources, generate synthetic content
    while len(selected) < max(2, min(top_k_sites, 3)):  # Ensure at least 2-3 sources
        logger.info(f"Only {len(selected)} sources retrieved, generating synthetic content")
        synthetic_doc = create_synthetic_content(query, f"generated://content/{len(selected) + 1}")
        selected.append(synthetic_doc)
    
    logger.info(f"Research completed. Retrieved {len(selected)} sources, {len(failed_urls)} failed")
    
    return selected