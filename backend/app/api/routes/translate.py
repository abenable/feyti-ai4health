import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import require_dossier_root
from app.models.schemas import TranslationRequest
from app.services import translation_service
from app.services.dossier_service import (
    resolve_document_paths,
    read_generated,
    read_meta,
    write_generated,
    _meta_path,
)
from app.services.store_utils import write_json

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=dict)
async def translate(request: TranslationRequest, root: Path = Depends(require_dossier_root)):
    """Translate a section's generated markdown into the target language.

    The original ``<stem>.generated.md`` is never overwritten. The translation is
    written to ``<stem>.<lang>.generated.md`` and the metadata side‑car is updated
    with language information.
    """
    # Resolve paths and load the source markdown.
    paths = resolve_document_paths(root, request.section_path, request.stem)
    original = read_generated(paths["section_dir"], request.stem)
    if not original:
        raise HTTPException(status_code=404, detail="Source generated markdown not found")

    # Perform translation.
    outcome = await translation_service.translate_text(
        original, source_language="en", target_language=request.target_language
    )

    # Write translated file.
    translated_path = paths["section_dir"] / f"{request.stem}.{request.target_language}.generated.md"
    translated_path.write_text(outcome.text)

    # Update meta side‑car.
    meta = read_meta(paths["section_dir"], request.stem)
    meta.update({
        "language": request.target_language,
        "translated_at": datetime.now(timezone.utc).isoformat(),
    })
    write_json(_meta_path(paths["section_dir"], request.stem), meta)

    return {"stem": request.stem, "language": request.target_language, "file": translated_path.name}


@router.get("/status")
async def status(section_path: str = Query(...), root: Path = Depends(require_dossier_root)):
    """Return translation availability for each document in *section_path*.

    Example response::
        [{"stem": "section1", "language": "en", "available": ["fr", "pt"]}, ...]
    """
    # Resolve the section directory.
    try:
        from app.services.dossier_service import _resolve_section_dir
        section_dir = _resolve_section_dir(root, section_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    stems: dict[str, set[str]] = {}
    for p in section_dir.iterdir():
        if not p.is_file() or not p.name.endswith(".generated.md"):
            continue
        name = p.stem
        # Determine stem and language based on filename pattern.
        parts = name.split(".")
        if len(parts) == 2 and parts[1] == "generated":
            # Original file: stem.generated
            stem = parts[0]
            stems.setdefault(stem, {"en"})
        elif len(parts) == 3 and parts[2] == "generated":
            # Language‑specific file: stem.lang.generated
            stem = parts[0]
            lang = parts[1]
            langs = stems.setdefault(stem, {"en"})
            langs.add(lang)
        else:
            # Fallback: treat as original stem.
            stem = name
            stems.setdefault(stem, {"en"})
    result = []
    for stem, langs in stems.items():
        result.append({"stem": stem, "language": "en", "available": sorted(langs)})
    return result

