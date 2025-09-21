# utils.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

HEADERS = {
    "User-Agent": "ResearchAgent/1.0 (+https://example.com) Python/requests"
}

def safe_get(url, timeout=8, max_tries=2, backoff=1.0):
    """Simple GET with basic retry/backoff and user-agent."""
    tries = 0
    while tries < max_tries:
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            tries += 1
            if tries >= max_tries:
                raise
            time.sleep(backoff * tries)
    raise RuntimeError("unreachable")

def extract_text_from_html(html):
    """Return a cleaned, best-effort main text from HTML (first readable paragraphs)."""
    soup = BeautifulSoup(html, "lxml")

    # remove scripts/styles
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "aside", "form"]):
        tag.decompose()

    # Try to get useful text: paragraphs, headings
    paragraphs = []
    for el in soup.find_all(["h1","h2","h3","p"]):
        text = el.get_text(separator=" ", strip=True)
        if text:
            paragraphs.append(text)
    # Fallback: whole body text
    if not paragraphs:
        body = soup.find("body")
        if body:
            text = body.get_text(separator=" ", strip=True)
            paragraphs = re.split(r'(?<=\.)\s+', text)[:10]

    # join first few paragraphs to limit verbosity
    joined = "\n\n".join(paragraphs[:6])
    # minimal cleaning
    joined = re.sub(r'\s+', ' ', joined).strip()
    return joined

def normalize_url(base_url, link):
    try:
        return urljoin(base_url, link)
    except:
        return link

def domain_from_url(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return url
