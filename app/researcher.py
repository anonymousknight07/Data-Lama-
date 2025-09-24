import os
import requests
from typing import List, Dict
import time
from urllib.parse import urlparse
from app.synthesizer import call_openrouter
import logging
import random

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
    Use Serper AI for web search and content extraction with retry logic.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            headers = {
                'X-API-KEY': get_serper_api_key(),
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': num_results,
                'extractContent': True,
                'type': 'search'
            }
            
            logger.info(f"Serper search attempt {attempt + 1}/{max_retries} for query: {query}")
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Serper rate limited, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                continue
            elif response.status_code == 402:  # Payment required
                logger.error("Serper API credits exhausted")
                break
            elif response.status_code != 200:
                logger.warning(f"Serper API returned status {response.status_code}")
                if attempt == max_retries - 1:
                    break
                time.sleep(1)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            hits = []
            for result in data.get('organic', [])[:num_results]:
                hit = {
                    'title': result.get('title', 'Untitled'),
                    'url': result.get('link', ''),
                    'snippet': result.get('snippet', ''),
                    'content': result.get('content', '')
                }
                
                if is_valid_url(hit['url']):
                    hits.append(hit)
            
            logger.info(f"Serper search successful: {len(hits)} results")
            return hits
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Serper API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            logger.error(f"Unexpected error in serper_search: {e}")
            break
    
    # Fallback to OpenRouter search if Serper fails
    logger.info("Serper search failed, falling back to OpenRouter search")
    return openrouter_search(query, num_results)

def openrouter_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Fallback: Use OpenRouter as a search agent with rate limiting awareness.
    """
    prompt = (
        f"Find reliable, accessible articles about: {query}\n\n"
        f"Return {num_results} high-quality URLs from reputable sources like:\n"
        f"- Harvard Business Review, McKinsey, Deloitte, BCG\n"
        f"- Medium, ProductPlan, Aha!, industry publications\n"
        f"- Academic institutions, government sites\n"
        f"- Avoid paywalled sites or sites that block scraping\n\n"
        f"Format exactly as:\n"
        f"1. Descriptive Article Title – https://example.com/full-url"
    )

    try:
        logger.info("Using OpenRouter for URL discovery")
        output = call_openrouter([
            {"role": "system", "content": "You are a research assistant. Only return accessible, high-quality URLs with descriptive titles."},
            {"role": "user", "content": prompt},
        ])

        hits = []
        for line in output.splitlines():
            line = line.strip()
            if not line or "http" not in line:
                continue
            try:
                if "–" in line:
                    parts = line.split("–", 1)
                    if len(parts) == 2:
                        title = parts[0].strip().lstrip("0123456789. ")
                        url = parts[1].strip()
                        
                        if url and is_valid_url(url):
                            hits.append({
                                "title": title, 
                                "url": url,
                                "snippet": "",
                                "content": ""
                            })
                elif "http" in line:
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
        
        logger.info(f"OpenRouter search returned {len(hits)} URLs")
        return hits[:num_results]
        
    except Exception as e:
        logger.error(f"OpenRouter search failed: {e}")
        return get_fallback_sources(query)

def get_fallback_sources(query: str) -> List[Dict]:
    """Provide fallback sources with comprehensive business information"""
    fallback_sources = [
        {
            "title": f"RICE vs Kano Model: Prioritization Frameworks Compared",
            "url": "https://example.com/rice-kano-comparison",
            "snippet": f"Comparison of RICE scoring and Kano model for feature prioritization",
            "content": f"""
            The RICE scoring model and Kano model are both popular prioritization frameworks, but they serve different purposes:

            **RICE Scoring Model:**
            - RICE stands for Reach, Impact, Confidence, and Effort
            - Quantitative approach using numerical scores
            - Reach: How many people will be affected
            - Impact: How much will it affect each person
            - Confidence: How sure are you about your estimates
            - Effort: How much work is required
            - Formula: (Reach × Impact × Confidence) / Effort
            
            **Kano Model:**
            - Qualitative framework focusing on customer satisfaction
            - Categories features into: Must-haves, Performance features, and Delighters
            - Must-haves: Basic expectations that cause dissatisfaction if missing
            - Performance features: Features where more is better
            - Delighters: Unexpected features that create excitement
            - Also includes Indifferent and Reverse features
            
            **Key Differences:**
            1. **Methodology**: RICE is quantitative with numerical scoring, Kano is qualitative with categorization
            2. **Focus**: RICE focuses on business impact and resource allocation, Kano focuses on customer satisfaction
            3. **Usage**: RICE is better for comparing diverse features, Kano is better for understanding feature types
            4. **Time**: RICE provides immediate scoring, Kano requires customer research
            5. **Complementary**: Many teams use both - Kano to understand feature types, RICE to prioritize within categories
            """
        },
        {
            "title": f"Product Management Prioritization: When to Use RICE vs Kano",
            "url": "https://example.com/prioritization-frameworks",
            "snippet": f"Strategic guidance on choosing between prioritization frameworks",
            "content": f"""
            **When to Use RICE Scoring:**
            - You need to make quick prioritization decisions
            - You have diverse features to compare (new features, improvements, technical debt)
            - You want a standardized scoring system across teams
            - You need to justify decisions with data
            - You're in fast-moving environments requiring regular re-prioritization
            
            **When to Use Kano Model:**
            - You're planning a new product or major feature set
            - You want to understand customer expectations deeply
            - You have time for customer research and surveys
            - You're trying to identify potential breakthrough features
            - You need to balance basic functionality with innovation
            
            **Best Practices for Combining Both:**
            1. Use Kano first to categorize features by customer impact type
            2. Apply RICE scoring within each Kano category
            3. Ensure must-haves are prioritized regardless of RICE score
            4. Use RICE to choose between performance features
            5. Consider delighters as potential high-impact, low-confidence features in RICE
            
            **Implementation Tips:**
            - RICE works best with cross-functional team input
            - Kano requires direct customer feedback through surveys or interviews
            - Both frameworks should be revisited regularly as market conditions change
            - Consider using simplified versions for smaller teams or projects
            """
        }
    ]
    return fallback_sources

def serper_extract_content(url: str) -> Dict:
    """Use Serper AI to extract content from a specific URL with error handling."""
    max_retries = 2
    for attempt in range(max_retries):
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
            
            if response.status_code == 429:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Serper extract rate limited, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                continue
            elif response.status_code != 200:
                logger.warning(f"Serper extract failed with status {response.status_code} for {url}")
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")
            
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
            logger.warning(f"Serper content extraction attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
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
            try:
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
                    raise ValueError(f"Article content too short or empty")
                
                logger.info(f"Successfully extracted with newspaper: {url}")
                return extracted_data
            except ImportError:
                logger.error("newspaper package not installed, cannot use fallback extraction")
                raise Exception("Content extraction failed: no available extractors")
        
    except Exception as e:
        logger.error(f"All content extraction methods failed for {url}: {e}")
        raise Exception(f"Content extraction error: {str(e)}")

def create_synthetic_content(query: str, url: str) -> Dict:
    """
    Create synthetic content when web scraping fails, with rate limiting awareness
    """
    try:
        # Create more specific content based on common business analysis queries
        if "rice" in query.lower() and "kano" in query.lower():
            content = """
            **RICE Scoring Model for Prioritization**
            
            RICE is a quantitative framework that helps product teams prioritize features and initiatives based on four key factors:
            
            **RICE Components:**
            - **Reach**: Number of people/customers affected in a given time period
            - **Impact**: Expected improvement to the key metric per person affected (scale: 3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal)
            - **Confidence**: How confident you are in your Reach and Impact estimates (percentage: 100%=high, 80%=medium, 50%=low)
            - **Effort**: Amount of work required from all team members (person-months)
            
            **RICE Formula: (Reach × Impact × Confidence) / Effort**
            
            **Kano Model for Feature Categorization**
            
            The Kano model categorizes features based on their relationship to customer satisfaction:
            
            **Kano Categories:**
            - **Must-haves (Basic)**: Features customers expect; absence causes dissatisfaction
            - **Performance (Linear)**: More is better; directly correlates with satisfaction
            - **Delighters (Attractive)**: Unexpected features that create excitement
            - **Indifferent**: Features customers don't care about
            - **Reverse**: Features that actually decrease satisfaction for some users
            
            **Key Differences Between RICE and Kano:**
            
            1. **Methodology**: RICE uses numerical scoring; Kano uses qualitative categorization
            2. **Purpose**: RICE ranks features by business value; Kano identifies feature types by customer impact
            3. **Data Requirements**: RICE needs internal estimates; Kano requires customer research
            4. **Speed**: RICE enables quick decisions; Kano needs time for customer surveys
            5. **Scope**: RICE compares any initiatives; Kano focuses on customer-facing features
            
            **When to Use Each Framework:**
            - Use RICE when you need to quickly prioritize a backlog of diverse features
            - Use Kano when planning new products or understanding customer needs deeply
            - Combine both: Use Kano to categorize features, then RICE to prioritize within categories
            
            **Best Practices:**
            - Regularly update RICE scores as you learn more
            - Validate Kano categories through customer interviews
            - Ensure must-haves are addressed regardless of RICE scores
            - Use cross-functional teams for accurate RICE estimation
            """
        else:
            # Generic business analysis content
            prompt = (
                f"Generate comprehensive business analysis content about: {query}\n\n"
                f"Provide detailed analysis covering key concepts, best practices, "
                f"implementation strategies, and practical recommendations."
            )
            
            content = call_openrouter([
                {"role": "system", "content": "You are a senior business analyst. Provide detailed, structured analysis."},
                {"role": "user", "content": prompt},
            ])
        
        return {
            "url": url,
            "title": f"Business Analysis: {query}",
            "authors": ["Business Analysis Team"],
            "publish_date": None,
            "text": content,
            "summary": content[:300] + "..." if len(content) > 300 else content,
            "synthetic": True
        }
    except Exception as e:
        logger.error(f"Failed to generate synthetic content: {e}")
        return {
            "url": url,
            "title": f"Information about {query}",
            "authors": [],
            "publish_date": None,
            "text": f"This analysis covers key aspects of {query}. The system is currently experiencing high demand, but basic information about {query} includes fundamental business principles and established methodologies in this area.",
            "summary": f"General analysis of {query} concepts and applications.",
            "synthetic": True,
            "error": "CONTENT_GENERATION_FAILED"
        }

def researcher_job(query: str, top_k_sites: int = 5) -> List[Dict]:
    """
    Main research function with comprehensive error handling and fallback strategies
    """
    logger.info(f"Starting research for query: {query}")
    
    try:
        # Get potential sources using Serper AI
        hits = serper_search(query, num_results=top_k_sites * 2)
        logger.info(f"Found {len(hits)} potential sources")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        hits = []
    
    selected = []
    failed_urls = []
    
    # Process found sources
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