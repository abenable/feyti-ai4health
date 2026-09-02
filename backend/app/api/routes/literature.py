from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
import httpx
import os
from datetime import datetime, timezone

from app.api.deps import require_dossier_root
from app.services import db_repo
from app.services.dossier_service import _safe_dir_name, _safe_filename, slugify
from app.services.ctd_map import get_ctd_title

from app.services.lit_scrapers import run_all_scrapers
from app.services.lit_query_builder import build_search_params
from app.services.lit_ranker import rank_results

router = APIRouter()

# ---------------------------------------------------------------------------
# Helper models – kept lightweight to avoid pulling the whole schemas module.
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from typing import Optional, List, Dict

class SearchRequest(BaseModel):
    query: str
    region: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    topics: Optional[List[str]] = None

class FileRequest(BaseModel):
    query: str
    url: str

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/search")
async def search(req: SearchRequest, root: Path = Depends(require_dossier_root)):
    """Perform a literature search, rank results, and persist the outcome.

    The search parameters are built via ``build_search_params`` (LLM first,
    deterministic fallback). All scrapers run in parallel; failures are ignored.
    Results are deduplicated by DOI then URL, ranked, and saved as a
    literature_search feature record scoped to the dossier.
    """
    # 1. Build structured params (may use LLM).
    params = await build_search_params(req.query)
    # Override with explicit filters if provided.
    region = req.region or params.get("detected_region")
    date_from = req.date_from or params.get("detected_year_from")
    date_to = req.date_to or params.get("detected_year_to")
    topics = req.topics or params.get("detected_topics") or []

    # 2. Run all scrapers in parallel.
    raw_results = await run_all_scrapers(
        query=params.get("rewritten_query") or req.query,
        max_results=50,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        region=region,
    )

    # 3. Deduplicate – prefer DOI, then URL.
    seen = set()
    deduped: List[Dict] = []
    for r in raw_results:
        key = (r.get("doi") or "").lower() or r.get("url", "").lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(r)

    # 4. Rank results.
    ranked = await rank_results(req.query, deduped, region=region, topics=topics)

    # 5. Persist.
    dossier_id = db_repo.dossier_id_from_root(root)
    safe_name = _safe_filename(req.query)
    payload = {
        "query": req.query,
        "params": params,
        "saved_at": datetime.utcnow().isoformat(),
        "results": ranked,
    }
    db_repo.feature_put(dossier_id, "literature_search", safe_name, payload)
    return ranked


@router.get("/searches")
def list_searches(root: Path = Depends(require_dossier_root)):
    """List past literature searches stored for the dossier.

    Returns a list of objects ``{"query": <query>, "count": <result count>, "date": <ISO timestamp>}``.
    """
    dossier_id = db_repo.dossier_id_from_root(root)
    entries = []
    for row in db_repo.feature_list(dossier_id, "literature_search"):
        data = row.data or {}
        entries.append(
            {
                "query": data.get("query", row.record_key),
                "count": len(data.get("results", [])),
                "date": data.get("saved_at", row.created_at.isoformat()),
            }
        )
    # Most recent first
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


@router.get("/searches/{query}")
def get_search(query: str, root: Path = Depends(require_dossier_root)):
    """Replay a saved search identified by its original query string.
    """
    dossier_id = db_repo.dossier_id_from_root(root)
    row = db_repo.feature_get(dossier_id, "literature_search", _safe_filename(query))
    if row is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return row.data


@router.post("/file")
async def file_reference(req: FileRequest, root: Path = Depends(require_dossier_root)):
    """Fetch a URL (if possible) and file it into the dossier under Module 5.

    The fetched content (or an empty placeholder on failure) is stored as the
    document's original bytes in the *Other Study Reports* section (CTD path
    ``5.3.5.4``). The metadata records the original URL and source.
    """
    # Fetch the page – ignore errors.
    content = ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()
            content = resp.text
    except Exception:
        content = ""

    # Derive a safe stem from the URL.
    from urllib.parse import urlparse, unquote
    parsed = urlparse(req.url)
    stem_candidate = os.path.basename(parsed.path) or "reference"
    stem_candidate = unquote(stem_candidate).split("?")[0]
    stem = slugify(stem_candidate) or "reference"

    # File into the CTD section for Module 5 – Other Study Reports.
    ctd_path = "5.3.5.4"
    module = "Module 5 — Clinical"
    title = get_ctd_title(ctd_path) or "Other Study Reports"
    module_dir = _safe_dir_name(module)
    section_dir_name = _safe_dir_name(f"{ctd_path} {title}")
    section_path = f"{module_dir}/{section_dir_name}"

    dossier_id = db_repo.dossier_id_from_root(root)
    db_repo.ensure_dossier_row(dossier_id)
    db_repo.upsert_document(
        dossier_id, section_path, stem,
        module=module, ctd_path=ctd_path, title=title,
        filename=f"{stem}.reference.md",
        original_data=content.encode("utf-8"),
        extracted_text="", pages=[],
        meta={
            "reference_url": req.url,
            "source": "literature",
            "stem": stem,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
        generated_markdown="", status="draft",
    )
    return {"status": "filed", "stem": stem}


@router.get("/health")
async def health(dossier_id: str):
    return {"feature": "literature", "status": "ok"}
