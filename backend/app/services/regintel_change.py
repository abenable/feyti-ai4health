import difflib
from datetime import datetime
from typing import Optional

from app.models.regintel_schemas import ChangeRecord
from app.services.llm import generate_text
from app.services.regintel_store import add_change


def _build_text_diff(old_text: str, new_text: str, context_lines: int = 3) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="previous",
            tofile="current",
            n=context_lines,
        )
    )
    return "".join(diff)[:3000]


def _generate_ai_diff_summary(title: str, old_text: str, new_text: str, similarity: float) -> Optional[str]:
    diff_excerpt = _build_text_diff(old_text, new_text)
    if not diff_excerpt.strip():
        return None
    prompt = (
        f"You are a regulatory compliance analyst. Two versions of a regulatory document have been detected.\n\n"
        f"Document title: {title}\n"
        f"Similarity score: {similarity:.0%}\n"
        f"TEXT DIFF (unified format):\n{diff_excerpt}\n\n"
        "In 3-5 concise bullet points: what changed, compliance impact, required action."
    )
    try:
        summary = generate_text(prompt, max_tokens=500)
        return summary.strip() if summary else None
    except Exception:
        return None


def detect_change(url: str, source_key: str, old_text: str, new_text: str) -> ChangeRecord:
    """Detect change between two versions of a document.
    Returns a ChangeRecord (also persisted).
    """
    similarity = difflib.SequenceMatcher(None, old_text, new_text).ratio()
    old_hash = _content_hash(old_text) if (old_hash := None) is None else None
    # Compute hashes
    old_hash = _content_hash(old_text)
    new_hash = _content_hash(new_text)
    summary = None
    if similarity < 0.95:
        # Attempt AI summary; title may be derived from URL basename
        title = url.split('/')[-1] or "Document"
        summary = _generate_ai_diff_summary(title, old_text, new_text, similarity)
    record = ChangeRecord(
        url=url,
        source_key=source_key,
        old_hash=old_hash,
        new_hash=new_hash,
        similarity=similarity,
        summary=summary,
    )
    add_change(record)
    return record


def _content_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()
