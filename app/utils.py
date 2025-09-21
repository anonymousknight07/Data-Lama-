from typing import List

def chunk_text(text: str, max_chars: int = 2500) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    cur = ""
    out = []
    for p in paragraphs:
        if not cur:
            cur = p
        elif len(cur) + len(p) + 2 > max_chars:
            out.append(cur)
            cur = p
        else:
            cur = cur + "\n\n" + p
    if cur:
        out.append(cur)
    return out

def build_citation_list(sources: List[dict]) -> List[str]:
    citations = []
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or s.get("url")
        citations.append(f"[{i}] {title} — {s.get('url')}")
    return citations

def format_superscripts(text: str, citations: list) -> str:
    """
    Replace [i] markers in the answer with HTML superscript citation links.
    Example: "RICE model [1]" → RICE model<sup><a href="url">[1]</a></sup>
    """
    formatted = text
    for i, c in enumerate(citations, start=1):
        # Extract URL from the citation string "[i] title — url"
        parts = c.split("—")
        url = parts[-1].strip() if len(parts) > 1 else "#"
        formatted = formatted.replace(
            f"[{i}]",
            f'<sup><a href="{url}" target="_blank" rel="noopener">[{i}]</a></sup>'
        )
    return formatted