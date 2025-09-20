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
