# researcher.py
import os
import requests
from newspaper import Article
from typing import List, Dict
import time
from urllib.parse import urlparse
from app.synthesizer import call_openrouter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if URL is valid and accessible"""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
    except Exception:
        return False

def openrouter_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Use OpenRouter as a search agent.
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
                            hits.append({"title": title, "url": url})
                elif "http" in line:
                    # Fallback: extract URL from line
                    import re
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match and is_valid_url(url_match.group()):
                        url = url_match.group()
                        title = line.replace(url, "").strip().lstrip("0123456789.- ")
                        hits.append({"title": title or "Article", "url": url})
            except Exception as e:
                logger.warning(f"Error parsing line: {line}, error: {e}")
                continue
        
        return hits[:num_results]
    except Exception as e:
        logger.error(f"Error in openrouter_search: {e}")
        # Fallback to some default authoritative sources
        return get_fallback_sources(query)

def get_fallback_sources(query: str) -> List[Dict]:
    """Provide fallback sources when OpenRouter search fails"""
    fallback_sources = [
        {
            "title": f"Harvard Business Review insights on {query}",
            "url": "https://hbr.org"
        },
        {
            "title": f"McKinsey analysis of {query}",
            "url": "https://mckinsey.com"
        },
        {
            "title": f"Medium articles about {query}",
            "url": "https://medium.com"
        }
    ]
    return fallback_sources[:3]

def fetch_and_extract(url: str, timeout: int = 10) -> Dict:
    """
    Fetch and extract content with comprehensive error handling
    """
    try:
        # Set up custom headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # Create article with custom config
        article = Article(url)
        article.set_authors([])
        article.set_publish_date()
        
        # Download with timeout and custom headers
        session = requests.Session()
        session.headers.update(headers)
        
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # Exponential backoff
        
        article.set_html(response.text)
        article.parse()
        
        # Try NLP processing
        try:
            article.nlp()
        except Exception as nlp_error:
            logger.warning(f"NLP processing failed for {url}: {nlp_error}")
        
        # Ensure we have some content
        if not article.text or len(article.text.strip()) < 100:
            raise ValueError("Article content too short or empty")
        
        return {
            "url": url,
            "title": article.title or "Untitled Article",
            "authors": article.authors or [],
            "publish_date": str(article.publish_date) if article.publish_date else None,
            "text": article.text,
            "summary": getattr(article, "summary", None) or article.text[:500] + "...",
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"403 Forbidden for {url} - site blocks scraping")
            raise Exception(f"Site blocks access (403 Forbidden)")
        elif e.response.status_code == 404:
            logger.error(f"404 Not Found for {url}")
            raise Exception(f"Page not found (404)")
        else:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            raise Exception(f"HTTP error: {e.response.status_code}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for {url}")
        raise Exception(f"Request timeout")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for {url}: {e}")
        raise Exception(f"Connection failed")
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
    Main research function with comprehensive error handling
    """
    logger.info(f"Starting research for query: {query}")
    
    # Get potential sources
    hits = openrouter_search(query, num_results=top_k_sites * 2)
    logger.info(f"Found {len(hits)} potential sources")
    
    selected = []
    failed_urls = []
    
    for h in hits:
        if len(selected) >= top_k_sites:
            break
            
        try:
            logger.info(f"Attempting to fetch: {h.get('url')}")
            doc = fetch_and_extract(h["url"])
            doc["source_snippet"] = h.get("title")
            selected.append(doc)
            logger.info(f"Successfully fetched: {h.get('url')}")
            
        except Exception as e:
            failed_urls.append(h["url"])
            logger.warning(f"Failed to fetch {h.get('url')}: {e}")
            continue
    
    # If we don't have enough sources, generate synthetic content
    while len(selected) < max(2, min(top_k_sites, 3)):  # Ensure at least 2-3 sources
        logger.info(f"Only {len(selected)} sources retrieved, generating synthetic content")
        synthetic_doc = create_synthetic_content(query, f"generated://content/{len(selected) + 1}")
        selected.append(synthetic_doc)
    
    logger.info(f"Research completed. Retrieved {len(selected)} sources, {len(failed_urls)} failed")
    
    return selected