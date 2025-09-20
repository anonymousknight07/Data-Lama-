import os
import requests
from newspaper import Article
from typing import List, Dict

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SEARCH_URL = "https://google.serper.dev/search"


def search_serper(query: str, num_results: int = 10) -> List[Dict]:
    if not SERPER_API_KEY:
        raise RuntimeError("SERPER_API_KEY not set. See .env file")

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": num_results}

    resp = requests.post(SEARCH_URL, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("organic", [])
    out = []
    for r in results:
        url = r.get("link") or r.get("url")
        if not url:
            continue
        out.append({"title": r.get("title"), "url": url, "snippet": r.get("snippet")})
    return out


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
    hits = search_serper(query, num_results=20)
    selected = []
    for h in hits:
        if len(selected) >= top_k_sites:
            break
        try:
            doc = fetch_and_extract(h["url"])
            doc["source_snippet"] = h.get("snippet")
            selected.append(doc)
        except Exception as e:
            print("fetch failed", h.get("url"), e)
    return selected




# import os
# import requests
# from newspaper import Article
# from typing import List, Dict

# SERPAPI_KEY = os.getenv("SERPAPI_KEY")
# SEARCH_URL = "https://serpapi.com/search.json"

# def search_serpapi(query: str, num_results: int = 10) -> List[Dict]:
#     if not SERPAPI_KEY:
#         raise RuntimeError("SERPAPI_KEY not set. See .env file")
#     params = {"q": query, "engine": "google", "api_key": SERPAPI_KEY, "num": num_results}
#     resp = requests.get(SEARCH_URL, params=params, timeout=15)
#     resp.raise_for_status()
#     data = resp.json()
#     results = data.get("organic_results") or data.get("organic") or []
#     out = []
#     for r in results:
#         url = r.get("link") or r.get("url")
#         if not url:
#             continue
#         out.append({"title": r.get("title"), "url": url, "snippet": r.get("snippet")})
#     return out

# def fetch_and_extract(url: str) -> Dict:
#     a = Article(url)
#     a.download()
#     a.parse()
#     try:
#         a.nlp()
#     except Exception:
#         pass
#     return {
#         "url": url,
#         "title": a.title,
#         "authors": a.authors,
#         "publish_date": str(a.publish_date) if a.publish_date else None,
#         "text": a.text,
#         "summary": getattr(a, "summary", None),
#     }

# def researcher_job(query: str, top_k_sites: int = 5) -> List[Dict]:
#     hits = search_serpapi(query, num_results=20)
#     selected = []
#     for h in hits:
#         if len(selected) >= top_k_sites:
#             break
#         try:
#             doc = fetch_and_extract(h["url"])
#             doc["source_snippet"] = h.get("snippet")
#             selected.append(doc)
#         except Exception as e:
#             print("fetch failed", h.get("url"), e)
#     return selected
