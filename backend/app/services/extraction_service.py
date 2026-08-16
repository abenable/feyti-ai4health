"""Structured information extraction for a filed CTD document.

Runs one Gemini/DeepSeek structured-output call, same pattern as
classification_service.classify(). The requested field set is section-aware —
driven off the classified CTD path prefix — so a stability report is asked for
batches/conditions/timepoints while a GMP certificate is asked for
site/certificate number/expiry.

Never invents a value: a field the source doesn't state comes back "" and
reads as a gap, the same rule generation_service uses for its GAP_MARKER.
"""

from __future__ import annotations

import json
import logging

from app.core.exceptions import DocumentAnalysisError
from app.services.dossier_service import context_block
from app.services.llm import generate_json

logger = logging.getLogger(__name__)

# Section-path prefix → fields worth pulling. Longest matching prefix wins;
# falls back to _DEFAULT_FIELDS for anything uncovered.
FIELD_HINTS: dict[str, list[str]] = {
    "1.": ["applicant / manufacturer", "product name", "regulatory authority",
           "certificate or reference number", "issue date", "expiry date"],
    "3.2.S": ["substance name", "manufacturer", "manufacturing site address",
              "specification limits", "batch number"],
    "3.2.P.8": ["batch numbers", "storage conditions", "study timepoints",
                "assay results", "shelf life / retest period"],
    "3.2.P": ["product name", "strength", "dosage form", "batch number",
              "manufacturing site"],
    "4.2": ["species / model", "dose levels", "study duration", "key findings"],
    "5.3": ["study identifier", "study design", "population size",
            "primary endpoint", "key results"],
}
_DEFAULT_FIELDS = ["key dates", "reference/identification numbers", "named parties",
                    "quantitative results"]


def _fields_for(section_path: str) -> list[str]:
    best_prefix, best_fields = "", _DEFAULT_FIELDS
    for prefix, fields in FIELD_HINTS.items():
        if section_path.startswith(prefix) and len(prefix) > len(best_prefix):
            best_prefix, best_fields = prefix, fields
    return best_fields


def _build_prompt(text: str, classification: dict) -> str:
    section_path = classification.get("section_path", "")
    title = classification.get("title", "")
    fields = _fields_for(section_path)
    product = context_block("PRODUCT CONTEXT:")

    return (
        "You are a regulatory document analyst extracting structured facts from "
        f"a CTD section {section_path}: {title}.\n"
        "The DOCUMENT text may come from OCR and contain noise — interpret and "
        "silently correct obvious errors as you read.\n\n"
        + (f"{product}\n\n" if product else "")
        + f"Extract these fields if the document states them:\n"
        + "\n".join(f"- {f}" for f in fields)
        + "\n\nCRITICAL: only extract a value the document actually states. If a "
        "field is not present, return it with value \"\" — never guess or infer. "
        "For every field you DO extract, cite the page number it came from if "
        "page markers are present in the text below (else 0), and give a "
        "confidence 0.0-1.0 for how clearly the source states it.\n\n"
        f"DOCUMENT (first 8000 chars):\n{text[:8000]}\n\n"
        "Respond ONLY with JSON:\n"
        '{"fields": [{"label": "<field name>", "value": "<value or \\"\\">", '
        '"page": <int>, "confidence": 0.0-1.0}]}'
    )


async def extract_fields(text: str, classification: dict) -> list[dict]:
    """Return [{label, value, page, confidence}] for the section's field set."""
    if not text.strip():
        return []

    prompt = _build_prompt(text, classification)
    try:
        raw = await generate_json(prompt)
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DocumentAnalysisError(
            "Extraction service returned invalid JSON.", status_code=502
        ) from exc
    except Exception as exc:
        raise DocumentAnalysisError(
            f"Extraction service request failed: {exc}", status_code=502
        ) from exc

    fields = data.get("fields") or []
    if not isinstance(fields, list):
        return []

    out = []
    for f in fields:
        if not isinstance(f, dict) or not f.get("label"):
            continue
        out.append({
            "label": str(f["label"]),
            "value": str(f.get("value", "") or ""),
            "page": int(f.get("page") or 0),
            "confidence": float(f.get("confidence", 0.0) or 0.0),
        })
    return out


if __name__ == "__main__":  # ponytail self-check: python -m app.services.extraction_service
    assert _fields_for("3.2.P.8.3")[0] == "batch numbers"
    assert _fields_for("3.2.P.1") == FIELD_HINTS["3.2.P"]
    assert _fields_for("1.4") == FIELD_HINTS["1."]
    assert _fields_for("9.9.9") == _DEFAULT_FIELDS

    prompt = _build_prompt("Batch AB123 stored at 25C for 6 months.",
                            {"section_path": "3.2.P.8.3", "title": "Stability Data"})
    assert "never guess or infer" in prompt
    assert "batch numbers" in prompt
    print("OK — extraction_service field routing + no-inference prompt guardrail")
