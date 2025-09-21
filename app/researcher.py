# researcher.py
import os
import requests
from newspaper import Article
from typing import List, Dict
from app.synthesizer import call_openrouter  # reuse OpenRouter call

def openrouter_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Use OpenRouter as a search agent.
    Ask it to return a list of relevant URLs for the query.
    """
    prompt = (
        f"Search online for: {query}\n"
        f"Return the {num_results} most relevant, high-quality article or blog URLs.\n"
        f"Format strictly as a numbered list:\n"
        f"1. Title — URL"
    )

    output = call_openrouter([
        {"role": "system", "content": "You are a search assistant. Only return valid URLs with short titles."},
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
                title, url = line.split("—", 1)
                hits.append({"title": title.strip(" .0123456789"), "url": url.strip()})
        except Exception:
            continue
    return hits[:num_results]


def fetch_and_extract(url: str) -> Dict:
    a = Article(url)
    a.download()
    a.parse()
    try:
        a.nlp()
    except Exception:
        pass
    return {
        "url": url,
        "title": a.title,
        "authors": a.authors,
        "publish_date": str(a.publish_date) if a.publish_date else None,
        "text": a.text,
        "summary": getattr(a, "summary", None),
    }


def researcher_job(query: str, top_k_sites: int = 5) -> List[Dict]:
    hits = openrouter_search(query, num_results=top_k_sites * 2)  # fetch more in case some fail
    selected = []
    for h in hits:
        if len(selected) >= top_k_sites:
            break
        try:
            doc = fetch_and_extract(h["url"])
            doc["source_snippet"] = h.get("title")
            selected.append(doc)
        except Exception as e:
            print("fetch failed", h.get("url"), e)
    return selected
