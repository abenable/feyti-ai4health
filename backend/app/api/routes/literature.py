from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
import json
import httpx
import os
import asyncio
from datetime import datetime

from app.api.deps import require_dossier_root
from app.services.store_utils import safe_join, write_json, read_json
from app.services.dossier_service import dossier_root, _safe_filename, slugify
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
    Results are deduplicated by DOI then URL, ranked, and saved under
    ``dossiers/<id>/literature/<safe_query>.json``.
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
    safe_name = _safe_filename(req.query)
    literature_dir = safe_join(root, Path("literature"))
    os.makedirs(literature_dir, exist_ok=True)
    file_path = literature_dir / f"{safe_name}.json"
    payload = {
        "query": req.query,
        "params": params,
        "saved_at": datetime.utcnow().isoformat(),
        "results": ranked,
    }
    write_json(file_path, payload)
    return ranked


@router.get("/searches")
def list_searches(root: Path = Depends(require_dossier_root)):
    """List past literature searches stored under the dossier.

    Returns a list of objects ``{"query": <query>, "count": <result count>, "date": <ISO timestamp>}``.
    """
    literature_dir = safe_join(root, Path("literature"))
    if not literature_dir.is_dir():
        return []
    entries = []
    for entry in literature_dir.iterdir():
        if entry.suffix != ".json":
            continue
        data = read_json(entry)
        if not data:
            continue
        entries.append(
            {
                "query": data.get("query", entry.stem),
                "count": len(data.get("results", [])),
                "date": data.get("saved_at", datetime.fromtimestamp(entry.stat().st_mtime).isoformat()),
            }
        )
    # Most recent first
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


@router.get("/searches/{query}")
def get_search(query: str, root: Path = Depends(require_dossier_root)):
    """Replay a saved search identified by its original query string.
    """
    safe_name = _safe_filename(query)
    file_path = safe_join(root, Path(f"literature/{safe_name}.json"))
    data = read_json(file_path)
    if not data:
        raise HTTPException(status_code=404, detail="Search not found")
    return data


@router.post("/file")
async def file_reference(req: FileRequest, root: Path = Depends(require_dossier_root)):
    """Fetch a URL (if possible) and file it into the dossier under Module 5.

    The fetched content (or an empty placeholder on failure) is stored as
    ``<stem>.reference.md`` inside the *Other Study Reports* section (CTD path
    ``5.3.5.4``). A minimal metadata side‑car records the original URL and source.
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

    # Resolve the CTD section directory for Module 5 – Other Study Reports.
    ctd_path = "5.3.5.4"
    title = get_ctd_title(ctd_path) or "Other Study Reports"
    section_param = f"Module 5 — Clinical/{ctd_path} {title}"
    from app.services.dossier_service import resolve_document_paths
    paths = resolve_document_paths(root, section_param, stem)
    # Write markdown file.
    md_path = paths["section_dir"] / f"{stem}.reference.md"
    md_path.write_text(content, encoding="utf-8")
    # Write minimal meta JSON.
    meta = {"reference_url": req.url, "source": "literature"}
    write_json(paths["meta"], meta)
    return {"status": "filed", "stem": stem}


@router.get("/health")
async def health(dossier_id: str):
    return {"feature": "literature", "status": "ok"}

