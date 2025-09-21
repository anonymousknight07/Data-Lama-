import os
import requests
from app.utils import build_citation_list, format_superscripts

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-8b-instruct:free"


def get_api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set. See .env file")
    return key


def call_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }
    payload = {"model": MODEL, "messages": messages}
    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def extract_assertions_from_source(text: str, url: str):
    prompt = (
        f"Excerpt: {text[:500]}...\n\n"
        f"Source URL: {url}\n\n"
        "Summarize the key assertion(s) from this excerpt in 1–2 sentences."
    )
    try:
        output = call_openrouter([
            {"role": "system", "content": "You are a fact extractor."},
            {"role": "user", "content": prompt},
        ])
        return [{"assertion": output, "type": "note", "source": url}]
    except Exception:
        return [{"assertion": f"Fallback: {text[:100]}", "type": "note", "source": url}]


def synthesize_from_sources(question: str, sources: list) -> dict:
    citations = build_citation_list(sources)
    user_text = f"Question: {question}\n\nSources:\n" + "\n".join(citations)

    answer = call_openrouter([
        {"role": "system", "content": "You are an expert product manager. Answer clearly and cite relevant sources using [1], [2], etc."},
        {"role": "user", "content": user_text},
    ])

   
    formatted_answer = format_superscripts(answer, citations)

    return {"answer": formatted_answer, "citations": citations}
