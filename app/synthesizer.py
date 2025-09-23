import os
import requests
from app.utils import build_citation_list, format_superscripts

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-exp:free"


def get_api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set. See .env file")
    return key


def call_openrouter(messages):
    try:
        headers = {
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {"model": MODEL, "messages": messages}
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # Return a friendly fallback instead of crashing
        return f"⚠️ Unable to fetch model response: {str(e)}"


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

    # Pass only the question, let frontend handle Sources section
    user_text = (
        f"Question: {question}\n\n"
        "Answer clearly and cite sources inline using [1], [2], etc. "
        "Do NOT include a 'Sources' section."
    )

    answer = call_openrouter([
        {"role": "system", "content": "You are an expert business analyst. "
                                      "Provide a structured, professional answer. "
                                      "Cite sources inline with [1], [2], etc. "
                                      "Do NOT append a separate 'Sources' section."},
        {"role": "user", "content": user_text},
    ])

    # Format [1], [2], etc. into clickable superscripts
    formatted_answer = format_superscripts(answer, citations)

    return {"answer": formatted_answer, "citations": citations}
