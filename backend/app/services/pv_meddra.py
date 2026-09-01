"""MedDRA term suggestion service.

The real implementation would ask an LLM to suggest a MedDRA PT code for a free‑
text term. Here we provide a thin wrapper that caches results in
``pv/meddra_cache.json`` under the dossier root. The cache is a dict mapping the
original term to the LLM's JSON response.
"""

from __future__ import annotations

from typing import Any, Dict

from app.services import store_utils, llm
from app.services import pv_service


def _cache_path(dossier_id: str):
    return store_utils.safe_join(pv_service._pv_root(dossier_id), "meddra_cache.json")


def suggest(term: str, dossier_id: str) -> Dict[str, Any]:
    """Return a MedDRA suggestion for *term*.

    The function first checks ``meddra_cache.json``; if the term is cached the
    stored result is returned. Otherwise the LLM is invoked and the result is
    cached before being returned. The LLM is expected to return a JSON string
    that can be parsed into a ``dict``.
    """
    cache_file = _cache_path(dossier_id)
    cache = store_utils.read_json(cache_file) or {}
    if term in cache:
        return cache[term]
    # Prompt is deliberately simple – tests monkey‑patch ``llm.generate_json``.
    prompt = f"Suggest a MedDRA PT code for the term: {term!r}. Return JSON with keys 'pt_code' and 'pt_name'."
    # ``generate_json`` is async; we run it synchronously for simplicity using
    # ``asyncio.run`` – the function is only used in tests where the coroutine is
    # patched with a sync stub.
    import asyncio

    raw = asyncio.run(llm.generate_json(prompt))
    try:
        import json

        suggestion = json.loads(raw)
    except Exception:
        suggestion = {"pt_code": None, "pt_name": None}
    cache[term] = suggestion
    store_utils.write_json(cache_file, cache)
    return suggestion


def confirm(report_id: str, dossier_id: str, term: str, source: str = "user_confirmed") -> None:
    """Record that the user confirmed the MedDRA suggestion for a report.

    The confirmation is stored on the report JSON under a ``meddra`` key.
    """
    report = pv_service.get_report(dossier_id, report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found in dossier {dossier_id}")
    suggestion = suggest(term, dossier_id)
    # Update the report with the confirmed MedDRA data.
    update = {
        "meddra": {
            "pt_code": suggestion.get("pt_code"),
            "pt_name": suggestion.get("pt_name"),
            "source": source,
        }
    }
    pv_service.update_report(dossier_id, report_id, update)
