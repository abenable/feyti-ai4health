import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import require_dossier_root
from app.models.schemas import TranslationRequest
from app.services import db_repo, translation_service
from app.services.dossier_service import _resolve_section_dir, read_generated

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=dict)
async def translate(request: TranslationRequest, root: Path = Depends(require_dossier_root)):
    """Translate a section's generated markdown into the target language.

    The original generated markdown is never overwritten. The translation is
    stored on the document's `translations` map ({lang: markdown}) and the
    metadata records which language was produced and when.
    """
    # Resolve paths and load the source markdown.
    section_dir = _resolve_section_dir(root, request.section_path)
    original = read_generated(section_dir, request.stem)
    if not original:
        raise HTTPException(status_code=404, detail="Source generated markdown not found")

    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, request.stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    if row is None:
        raise HTTPException(status_code=404, detail="Source generated markdown not found")

    # Perform translation.
    outcome = await translation_service.translate_text(
        original, source_language="en", target_language=request.target_language
    )

    # Store the translation alongside the original (never overwriting it).
    db_repo.update_document_fields(
        dossier_id, section_path, safe_stem,
        translations_patch={request.target_language: outcome.text},
        meta_patch={
            "language": request.target_language,
            "translated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "stem": request.stem,
        "language": request.target_language,
        "file": f"{request.stem}.{request.target_language}.generated.md",
    }


@router.get("/status")
async def status(section_path: str = Query(...), root: Path = Depends(require_dossier_root)):
    """Return translation availability for each document in *section_path*.

    Example response::
        [{"stem": "section1", "language": "en", "available": ["fr", "pt"]}, ...]
    """
    section_dir = _resolve_section_dir(root, section_path)
    dossier_id, section_path_key, _ = db_repo.doc_key(section_dir, "x")

    rows = [
        row for row in db_repo.list_documents(dossier_id)
        if row.section_path == section_path_key
        and ((row.generated_markdown or "").strip() or (row.translations or {}))
    ]
    result = []
    for row in sorted(rows, key=lambda r: r.stem):
        available = ["en"] + sorted((row.translations or {}).keys())
        result.append({"stem": row.stem, "language": "en", "available": available})
    return result
