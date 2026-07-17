import logging
import zipfile
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    DossierModule,
    DocumentDetail,
    EditRequest,
    FeedbackRequest,
    GenerateRequest,
    GenerateResponse,
    GeneratedDoc,
    ReviewStatus,
)
from app.services.dossier_service import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_EDITED,
    _safe_filename,
    list_generated_docs,
    load_extracted_text,
    read_generated,
    read_meta,
    read_status,
    write_generated,
    _resolve_section_dir,
)
from app.services.export_service import markdown_to_docx
from app.services.generation_service import generate_document

logger = logging.getLogger(__name__)
router = APIRouter()


def _stem_file(section_path: str, stem: str) -> tuple:
    """Resolve and return section_dir + safe stem, or raise HTTPException."""
    try:
        section_dir = _resolve_section_dir(section_path)
        safe_stem = _safe_filename(stem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return section_dir, safe_stem


@router.get("/tree", response_model=list[DossierModule])
def dossier_tree():
    from app.services.dossier_service import tree

    return tree()


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate or regenerate a CTD section draft."""
    section_dir, stem = _stem_file(request.section_path, request.stem)
    meta = read_meta(section_dir, stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    extracted_text = load_extracted_text(section_dir, meta)
    markdown = await generate_document(extracted_text, meta)
    status_record = read_status(section_dir, stem)
    write_generated(section_dir, stem, markdown, status=STATUS_DRAFT, feedback_history=status_record.get("feedback_history", []))
    return GenerateResponse(markdown=markdown, status=read_status(section_dir, stem)["status"])


@router.get("/documents", response_model=list[GeneratedDoc])
def documents():
    return [GeneratedDoc(**d) for d in list_generated_docs()]


@router.get("/document", response_model=DocumentDetail)
def document(section_path: str = Query(...), stem: str = Query(...)):
    section_dir, safe_stem = _stem_file(section_path, stem)
    markdown = read_generated(section_dir, safe_stem)
    status = read_status(section_dir, safe_stem)
    meta = read_meta(section_dir, safe_stem)
    return DocumentDetail(markdown=markdown, status=status["status"], meta=meta)


@router.put("/document", response_model=GenerateResponse)
def edit_document(request: EditRequest):
    section_dir, safe_stem = _stem_file(request.section_path, request.stem)
    status_record = read_status(section_dir, safe_stem)
    write_generated(
        section_dir,
        safe_stem,
        request.markdown,
        status=STATUS_EDITED,
        feedback_history=status_record.get("feedback_history", []),
    )
    return GenerateResponse(markdown=request.markdown, status=read_status(section_dir, safe_stem)["status"])


@router.post("/feedback", response_model=GenerateResponse)
async def feedback(request: FeedbackRequest):
    section_dir, safe_stem = _stem_file(request.section_path, request.stem)
    meta = read_meta(section_dir, safe_stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    prior_markdown = read_generated(section_dir, safe_stem)
    extracted_text = load_extracted_text(section_dir, meta)

    new_markdown = await generate_document(
        extracted_text,
        meta,
        prior_markdown=prior_markdown or None,
        feedback=request.feedback,
    )

    status_record = read_status(section_dir, safe_stem)
    history = status_record.get("feedback_history", [])
    from datetime import datetime, timezone

    history.append({"feedback": request.feedback, "regenerated_at": datetime.now(timezone.utc).isoformat()})
    write_generated(section_dir, safe_stem, new_markdown, status=STATUS_DRAFT, feedback_history=history)
    return GenerateResponse(markdown=new_markdown, status=read_status(section_dir, safe_stem)["status"])


@router.post("/approve", response_model=ReviewStatus)
def approve(request: GenerateRequest):
    section_dir, safe_stem = _stem_file(request.section_path, request.stem)
    status_record = read_status(section_dir, safe_stem)
    markdown = read_generated(section_dir, safe_stem)
    write_generated(
        section_dir,
        safe_stem,
        markdown,
        status=STATUS_APPROVED,
        feedback_history=status_record.get("feedback_history", []),
    )
    return ReviewStatus(**read_status(section_dir, safe_stem))


@router.get("/export")
def export(section_path: str = Query(...), stem: str = Query(...), format: str = Query("docx")):
    if format.lower() != "docx":
        raise HTTPException(status_code=400, detail="Only docx export is supported")
    section_dir, safe_stem = _stem_file(section_path, stem)
    markdown = read_generated(section_dir, safe_stem)
    if not markdown:
        raise HTTPException(status_code=404, detail="Generated document not found")
    meta = read_meta(section_dir, safe_stem)
    filename = f"{safe_stem}.docx"
    docx_bytes = markdown_to_docx(markdown, meta.get("title", safe_stem))
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/all")
def export_all(format: str = Query("docx")):
    if format.lower() != "docx":
        raise HTTPException(status_code=400, detail="Only docx export is supported")

    docs = list_generated_docs()
    approved = [d for d in docs if d.get("status") == STATUS_APPROVED]
    if not approved:
        raise HTTPException(status_code=404, detail="No approved documents to export")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in approved:
            try:
                section_dir, safe_stem = _stem_file(doc["section_path"], doc["stem"])
            except HTTPException as exc:
                logger.warning("export/all: skipping %s/%s — %s", doc.get("section_path"), doc.get("stem"), exc.detail)
                continue
            markdown = read_generated(section_dir, safe_stem)
            if not markdown:
                logger.warning("export/all: skipping %s/%s — no generated markdown", doc.get("section_path"), doc.get("stem"))
                continue
            docx_bytes = markdown_to_docx(markdown, doc.get("title", safe_stem))
            zf.writestr(f"{safe_stem}.docx", docx_bytes)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=dossier-approved.zip"},
    )
