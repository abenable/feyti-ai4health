"""LLM-suggested, user-confirmed MedDRA coding with a per-dossier cache."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from app.models.pv_schemas import ADRReport, MedDRACoding
from app.services import llm, pv_service, store_utils


def _cache_path(dossier_id: str):
    return store_utils.safe_join(pv_service._pv_root(dossier_id), "meddra_cache.json")


async def suggest(term: str, dossier_id: str) -> Dict[str, Any]:
    """Suggest an unconfirmed MedDRA preferred term for *term*.

    Cached suggestions are returned without another LLM call. If the LLM is
    unavailable or returns unusable JSON, the verbatim term is retained as the
    name with no code rather than inventing a licensed MedDRA code.
    """
    clean_term = term.strip()
    cache_file = _cache_path(dossier_id)
    cache = store_utils.read_json(cache_file) or {}
    cached = cache.get(clean_term)
    if isinstance(cached, dict):
        return {**cached, "source": "cache"}

    prompt = (
        "Suggest one MedDRA preferred term for this adverse reaction verbatim. "
        "Return JSON with keys pt_code, pt_name, and version. Use an empty "
        "pt_code if you are not certain of the code; never invent a code. "
        f"Reaction: {clean_term!r}"
    )
    try:
        raw = await llm.generate_json(prompt)
        suggestion = json.loads(raw)
        if not isinstance(suggestion, dict):
            raise ValueError("MedDRA suggestion is not an object")
    except Exception:
        suggestion = {"pt_code": "", "pt_name": clean_term, "version": None}

    suggestion = {
        "pt_code": str(suggestion.get("pt_code") or "").strip(),
        "pt_name": str(suggestion.get("pt_name") or clean_term).strip(),
        "version": suggestion.get("version"),
        "source": "llm_suggestion",
    }
    cache[clean_term] = suggestion
    store_utils.write_json(cache_file, cache)
    return suggestion


async def confirm(report_id: str, dossier_id: str, term: str) -> ADRReport:
    """Confirm a suggestion and persist it on the report reaction fields."""
    if pv_service.get_report(dossier_id, report_id) is None:
        raise ValueError(f"Report {report_id} not found in dossier {dossier_id}")

    suggestion = await suggest(term, dossier_id)
    coding = MedDRACoding(
        pt_code=str(suggestion.get("pt_code") or "").strip(),
        pt_name=str(suggestion.get("pt_name") or term).strip(),
        version=suggestion.get("version"),
        source="user_confirmed",
        confirmed_at=datetime.utcnow(),
    )
    updated = pv_service.update_report(
        dossier_id,
        report_id,
        {
            "reaction_pt_code": coding.pt_code or None,
            "reaction_pt_name": coding.pt_name or None,
            "meddra": coding.model_dump(mode="json"),
        },
    )
    if updated is None:
        raise ValueError(f"Report {report_id} not found in dossier {dossier_id}")
    return updated
