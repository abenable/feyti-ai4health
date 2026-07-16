"""Feyti CTD classification via one Gemini structured-output call."""

from __future__ import annotations

import json
import logging

from google.genai import types
from google.genai.errors import ClientError

from app.core.exceptions import DocumentAnalysisError
from app.core.config import settings
from app.services.ctd_map import CTD_MAP
from app.services.gemini_service import get_client

logger = logging.getLogger(__name__)

MODULE_NAMES = {
    "1": "Module 1 — Administrative",
    "2": "Module 2 — Summaries",
    "3": "Module 3 — Quality",
    "4": "Module 4 — Nonclinical",
    "5": "Module 5 — Clinical",
}

# Default fallback for empty/hallucinated classifications.
_FALLBACK_SECTION = "1.2"


async def classify(text: str) -> dict:
    """Return {section_path, title, module, confidence, justification}."""
    catalogue = "\n".join(f"{p}: {t}" for p, t in CTD_MAP.items())
    prompt = (
        "You are a regulatory document classifier for an ICH-M4 CTD dossier.\n"
        "Pick the ONE best-matching section for this document from the list.\n\n"
        f"SECTIONS:\n{catalogue}\n\n"
        f"DOCUMENT (first 6000 chars):\n{text[:6000]}\n\n"
        'Respond ONLY with JSON: {"section_path": "<exact path from the list>", '
        '"confidence": 0.0-1.0, "justification": "one sentence"}'
    )

    try:
        resp = await get_client().aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(resp.text)
    except ClientError as exc:
        raise DocumentAnalysisError(
            f"Classification service request failed: {exc}", status_code=502
        ) from exc
    except json.JSONDecodeError as exc:
        raise DocumentAnalysisError(
            "Classification service returned invalid JSON.", status_code=502
        ) from exc

    path = data.get("section_path")
    if path not in CTD_MAP:  # hallucinated / malformed path
        logger.warning("[classify] invalid section_path '%s'; falling back to %s", path, _FALLBACK_SECTION)
        path, data["confidence"] = _FALLBACK_SECTION, 0.0

    return {
        "section_path": path,
        "title": CTD_MAP[path],
        "module": MODULE_NAMES[path.split(".")[0]],
        "confidence": float(data.get("confidence", 0.0)),
        "justification": data.get("justification", ""),
    }
