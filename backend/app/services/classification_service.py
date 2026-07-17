"""Feyti CTD classification via one Gemini structured-output call."""

from __future__ import annotations

import json
import logging

from app.core.exceptions import DocumentAnalysisError
from app.services.ctd_map import CTD_MAP, MODULE_NAMES
from app.services.dossier_service import context_block
from app.services.llm import generate_json

logger = logging.getLogger(__name__)

# Default fallback for empty/hallucinated classifications.
_FALLBACK_SECTION = "1.2"


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


async def classify(text: str) -> dict:
    """Classify + summarize a document in one LLM call.

    Returns {section_path, title, module, confidence, justification, summary,
    key_points}. The model also cleans up OCR noise while it reads, so the
    summary/key_points are judge-ready even when the input is raw OCR text.
    """
    catalogue = "\n".join(f"{p}: {t}" for p, t in CTD_MAP.items())
    product = context_block("PRODUCT CONTEXT (this dossier is for the following product):")
    prompt = (
        "You are a regulatory document analyst for an ICH-M4 CTD dossier.\n"
        "The DOCUMENT text may come from OCR and contain noise — interpret and "
        "silently correct obvious errors as you read.\n"
        "Do two things: (1) pick the ONE best-matching CTD section from the list, "
        "(2) summarize the document.\n\n"
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
        raw = await generate_json(prompt)  # gemini | deepseek, per settings.LLM_PROVIDER
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DocumentAnalysisError(
            "Classification service returned invalid JSON.", status_code=502
        ) from exc
    except Exception as exc:  # network / API / provider errors
        raise DocumentAnalysisError(
            f"Classification service request failed: {exc}", status_code=502
        ) from exc

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
