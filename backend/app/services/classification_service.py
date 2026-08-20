"""Feyti CTD classification: section_path from the fine-tuned classifier
model, justification/summary/key_points from one LLM structured-output call.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.exceptions import DocumentAnalysisError
from app.services.ctd_map import CTD_MAP, MODULE_NAMES
from app.services.dossier_service import context_block
from app.services.llm import generate_json

logger = logging.getLogger(__name__)

# Default fallback for empty/hallucinated classifications.
_FALLBACK_SECTION = "1.2"

_CTD_MODEL_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def _classify_section(text: str) -> str | None:
    """Ask the fine-tuned CTD classifier for a section code. Returns None on
    any failure (offline box, bad response) so the caller falls back to the
    LLM's own guess instead of failing the whole request."""
    url = f"{settings.FEYTI_CTD_API_URL.rstrip('/')}/invocations"
    try:
        async with httpx.AsyncClient(timeout=_CTD_MODEL_TIMEOUT) as client:
            resp = await client.post(url, json={"document_text": text})
            resp.raise_for_status()
            return resp.json().get("ctd_section")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("[classify] CTD classifier model unreachable, falling back to LLM: %s", exc)
        return None


def _normalize_path(raw) -> str:
    """Coerce a model's section_path to a bare CTD path.

    Models (esp. DeepSeek) often echo the whole catalogue line
    "3.2.P.8.3: Stability Data (Drug Product)" instead of just "3.2.P.8.3".
    Take the leading token before any ':' or whitespace.
    """
    if not raw:
        return ""
    path = str(raw).strip()
    if path in CTD_MAP:
        return path
    candidate = path.split(":")[0].split()[0].strip().rstrip(".")
    return candidate


async def classify(text: str, root: Path) -> dict:
    """Classify with the fine-tuned model, then summarize with one LLM call.

    Returns {section_path, title, module, confidence, justification, summary,
    key_points}. The LLM also cleans up OCR noise while it reads, so the
    summary/key_points are judge-ready even when the input is raw OCR text.
    """
    model_section = await _classify_section(text)
    known_section = model_section if model_section in CTD_MAP else None

    catalogue = "\n".join(f"{p}: {t}" for p, t in CTD_MAP.items())
    product = context_block(root, "PRODUCT CONTEXT (this dossier is for the following product):")
    if known_section:
        task = (
            f"This document has already been classified under CTD section "
            f"{known_section}: {CTD_MAP[known_section]}.\n"
            "Do two things: (1) confirm that section_path in your JSON response, "
            "(2) summarize the document."
        )
    else:
        task = (
            "Do two things: (1) pick the ONE best-matching CTD section from the list, "
            "(2) summarize the document."
        )
    prompt = (
        "You are a regulatory document analyst for an ICH-M4 CTD dossier.\n"
        "The DOCUMENT text may come from OCR and contain noise — interpret and "
        "silently correct obvious errors as you read.\n"
        + task + "\n\n"
        + (f"{product}\n\n" if product else "")
        + f"SECTIONS:\n{catalogue}\n\n"
        f"DOCUMENT (first 8000 chars):\n{text[:8000]}\n\n"
        "Respond ONLY with JSON:\n"
        '{"section_path": "<exact path from the list, e.g. 3.2.P.8.3>", '
        '"confidence": 0.0-1.0, '
        '"justification": "one sentence on why this section", '
        '"summary": "2-3 sentence plain-language summary of the document", '
        '"key_points": ["short factual point", "..."]}'
    )

    try:
        raw = await generate_json(prompt)  # aicyclinder, falling back to kimi then gemini
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DocumentAnalysisError(
            "Classification service returned invalid JSON.", status_code=502
        ) from exc
    except Exception as exc:  # network / API / provider errors
        raise DocumentAnalysisError(
            f"Classification service request failed: {exc}", status_code=502
        ) from exc

    if known_section:
        # The fine-tuned classifier is authoritative when reachable; the LLM
        # call above is only for justification/summary/key_points text.
        path, data["confidence"] = known_section, 1.0
    else:
        path = _normalize_path(data.get("section_path"))
        if path not in CTD_MAP:  # hallucinated / malformed path
            logger.warning("[classify] invalid section_path '%s'; falling back to %s", data.get("section_path"), _FALLBACK_SECTION)
            path, data["confidence"] = _FALLBACK_SECTION, 0.0

    key_points = data.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = [str(key_points)]

    return {
        "section_path": path,
        "title": CTD_MAP[path],
        "module": MODULE_NAMES[path.split(".")[0]],
        "confidence": float(data.get("confidence", 0.0)),
        "justification": data.get("justification", ""),
        "summary": data.get("summary", ""),
        "key_points": [str(k) for k in key_points][:6],
    }
