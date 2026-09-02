import logging
import mimetypes
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import require_dossier_root
from app.models.schemas import (
    DossierModule,
    DocumentDetail,
    EditRequest,
    ExtractedField,
    FeedbackRequest,
    GenerateRequest,
    GenerateResponse,
    GeneratedDoc,
    NewSectionRequest,
    NewSectionResponse,
    PlanModule,
    ProductContext,
    ReadinessReport,
    ReclassifyRequest,
    ReclassifyResponse,
    ReviewStatus,
    SourceDoc,
    ValidationReport,
)
from app.services.dossier_service import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_EDITED,
    _safe_filename,
    build_plan,
    create_section_document,
    list_generated_docs,
    load_extracted_text,
    reclassify_document,
    read_context,
    read_generated,
    read_meta,
    read_status,
    tree as dossier_tree_fn,
    write_context,
    write_fields,
    write_generated,
    _resolve_section_dir,
)
from app.services.export_service import markdown_to_docx
from app.services.extraction_service import extract_fields
from app.services.generation_service import generate_document
from app.services.validation_service import run_checks, validate_document

logger = logging.getLogger(__name__)
router = APIRouter()


def _stem_file(root: Path, section_path: str, stem: str) -> tuple:
    """Resolve and return section_dir + safe stem, or raise HTTPException."""
    try:
        section_dir = _resolve_section_dir(root, section_path)
        safe_stem = _safe_filename(stem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return section_dir, safe_stem


@router.get("/tree", response_model=list[DossierModule])
def dossier_tree(root: Path = Depends(require_dossier_root)):
    return dossier_tree_fn(root)


@router.get("/context", response_model=ProductContext)
def get_context(root: Path = Depends(require_dossier_root)):
    """Return the dossier's saved product context (empty fields if none)."""
    return ProductContext(**read_context(root))


@router.put("/context", response_model=ProductContext)
def put_context(context: ProductContext, root: Path = Depends(require_dossier_root)):
    """Save the dossier's product context."""
    write_context(root, context.model_dump())
    return context


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, root: Path = Depends(require_dossier_root)):
    """Generate or regenerate a CTD section draft."""
    section_dir, stem = _stem_file(root, request.section_path, request.stem)
    meta = read_meta(section_dir, stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    extracted_text = load_extracted_text(section_dir, meta)
    markdown = await generate_document(extracted_text, meta, root, augment=request.augment)
    status_record = read_status(section_dir, stem)
    write_generated(section_dir, stem, markdown, status=STATUS_DRAFT, feedback_history=status_record.get("feedback_history", []))
    return GenerateResponse(markdown=markdown, status=read_status(section_dir, stem)["status"])


@router.post("/extract", response_model=list[ExtractedField])
async def extract(request: GenerateRequest, root: Path = Depends(require_dossier_root)):
    """(Re-)run structured field extraction for an already-filed document."""
    section_dir, stem = _stem_file(root, request.section_path, request.stem)
    meta = read_meta(section_dir, stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    extracted_text = load_extracted_text(section_dir, meta)
    fields = await extract_fields(extracted_text, meta, root)
    write_fields(section_dir, stem, fields)
    return [ExtractedField(**f) for f in fields]


@router.post("/reclassify", response_model=ReclassifyResponse)
def reclassify(request: ReclassifyRequest, root: Path = Depends(require_dossier_root)):
    """Move a mis-filed document to a different CTD section."""
    section_dir, stem = _stem_file(root, request.section_path, request.stem)
    from app.services.ctd_map import CTD_MAP, MODULE_NAMES

    title = CTD_MAP.get(request.ctd_path)
    if title is None:
        raise HTTPException(status_code=404, detail=f"Unknown CTD section: {request.ctd_path}")
    module = MODULE_NAMES.get(request.ctd_path.split(".")[0], "Other")

    try:
        result = reclassify_document(root, section_dir, stem, request.ctd_path, title, module)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReclassifyResponse(**result)


@router.get("/documents", response_model=list[GeneratedDoc])
def documents(root: Path = Depends(require_dossier_root)):
    return [GeneratedDoc(**d) for d in list_generated_docs(root)]


@router.get("/plan", response_model=list[PlanModule])
def plan(root: Path = Depends(require_dossier_root)):
    """Full CTD catalogue merged with filed documents (approved/in_review/empty)."""
    return build_plan(root)


@router.get("/readiness", response_model=ReadinessReport)
async def readiness(root: Path = Depends(require_dossier_root)):
    """AI submission-readiness report: deterministic score + AI verdict/blockers."""
    from app.services.readiness_service import analyze_readiness

    return await analyze_readiness(root)


@router.post("/section", response_model=NewSectionResponse)
async def create_section(request: NewSectionRequest, root: Path = Depends(require_dossier_root)):
    """Author a document for a CTD section that has no uploaded source.

    augment=True generates an AI skeleton (structure + '⚠️ TO BE PROVIDED' gaps,
    grounded in the product context); augment=False creates a blank draft to
    write by hand. Either way the section becomes a normal editable document.
    """
    from app.services.ctd_map import CTD_MAP, MODULE_NAMES

    title = CTD_MAP.get(request.ctd_path)
    if title is None:
        raise HTTPException(status_code=404, detail=f"Unknown CTD section: {request.ctd_path}")
    module = MODULE_NAMES.get(request.ctd_path.split(".")[0], "Other")

    info = create_section_document(root, request.ctd_path, title, module)
    section_dir, stem = info["section_dir"], info["stem"]
    meta = read_meta(section_dir, stem)

    if request.augment:
        markdown = await generate_document("", meta, root, augment=True)
    else:
        markdown = read_generated(section_dir, stem)  # "" for a brand-new blank

    status_record = read_status(section_dir, stem)
    write_generated(section_dir, stem, markdown, status=STATUS_DRAFT,
                    feedback_history=status_record.get("feedback_history", []))
    return NewSectionResponse(
        section_path=info["section_path"],
        stem=stem,
        markdown=markdown,
        status=read_status(section_dir, stem)["status"],
    )


@router.get("/source", response_model=SourceDoc)
def source(section_path: str = Query(...), stem: str = Query(...), root: Path = Depends(require_dossier_root)):
    """Page-indexed extracted text for the source viewer (empty pages → single
    pseudo-page from extracted_text for documents filed before this existed)."""
    section_dir, safe_stem = _stem_file(root, section_path, stem)
    meta = read_meta(section_dir, safe_stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    pages = meta.get("pages") or []
    if not pages and meta.get("extracted_text"):
        pages = [{"page": 1, "text": meta["extracted_text"], "is_ocr": meta.get("had_ocr", False)}]

    return SourceDoc(
        pages=pages,
        had_ocr=meta.get("had_ocr", False),
        extracted_chars=meta.get("extracted_chars", 0),
        filename=meta.get("filename", ""),
    )


@router.get("/original")
def original(section_path: str = Query(...), stem: str = Query(...), root: Path = Depends(require_dossier_root)):
    """Download the original uploaded file (source of the extracted text)."""
    from fastapi import Response

    from app.services import db_repo

    section_dir, safe_stem = _stem_file(root, section_path, stem)
    dossier_id, section_path_key, key_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path_key, key_stem)
    filename = (row.filename if row else "") or (read_meta(section_dir, safe_stem).get("filename") or "")
    if not filename:
        raise HTTPException(status_code=404, detail="No original file for this document (authored section).")
    if not row or not row.original_data:
        raise HTTPException(status_code=404, detail="Original file is missing from disk.")
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(
        content=row.original_data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/document", response_model=DocumentDetail)
def document(section_path: str = Query(...), stem: str = Query(...), root: Path = Depends(require_dossier_root)):
    section_dir, safe_stem = _stem_file(root, section_path, stem)
    markdown = read_generated(section_dir, safe_stem)
    status = read_status(section_dir, safe_stem)
    meta = read_meta(section_dir, safe_stem)
    return DocumentDetail(markdown=markdown, status=status["status"], meta=meta)


@router.put("/document", response_model=GenerateResponse)
def edit_document(request: EditRequest, root: Path = Depends(require_dossier_root)):
    section_dir, safe_stem = _stem_file(root, request.section_path, request.stem)
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
async def feedback(request: FeedbackRequest, root: Path = Depends(require_dossier_root)):
    section_dir, safe_stem = _stem_file(root, request.section_path, request.stem)
    meta = read_meta(section_dir, safe_stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    prior_markdown = read_generated(section_dir, safe_stem)
    extracted_text = load_extracted_text(section_dir, meta)

    new_markdown = await generate_document(
        extracted_text,
        meta,
        root,
        prior_markdown=prior_markdown or None,
        feedback=request.feedback,
    )

    status_record = read_status(section_dir, safe_stem)
    history = status_record.get("feedback_history", [])
    history.append({"feedback": request.feedback, "regenerated_at": datetime.now(timezone.utc).isoformat()})
    write_generated(section_dir, safe_stem, new_markdown, status=STATUS_DRAFT, feedback_history=history)
    return GenerateResponse(markdown=new_markdown, status=read_status(section_dir, safe_stem)["status"])


@router.get("/validate", response_model=ValidationReport)
async def validate(section_path: str = Query(...), stem: str = Query(...), root: Path = Depends(require_dossier_root)):
    """Output validation: deterministic checks + AI unsupported-claims pass.
    Approve is gated on this report having zero error-level checks."""
    section_dir, safe_stem = _stem_file(root, section_path, stem)
    meta = read_meta(section_dir, safe_stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Document metadata not found")

    markdown = read_generated(section_dir, safe_stem)
    extracted_text = load_extracted_text(section_dir, meta)
    report = await validate_document(markdown, extracted_text, meta)
    return ValidationReport(**report)


@router.post("/approve", response_model=ReviewStatus)
async def approve(request: GenerateRequest, root: Path = Depends(require_dossier_root)):
    section_dir, safe_stem = _stem_file(root, request.section_path, request.stem)
    meta = read_meta(section_dir, safe_stem)
    markdown = read_generated(section_dir, safe_stem)

    checks = run_checks(markdown, meta)
    errors = [c for c in checks if c["level"] == "error"]
    if errors:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot approve: {len(errors)} unresolved validation error(s). "
                    "Run /validate for details.",
        )

    status_record = read_status(section_dir, safe_stem)
    write_generated(
        section_dir,
        safe_stem,
        markdown,
        status=STATUS_APPROVED,
        feedback_history=status_record.get("feedback_history", []),
    )
    return ReviewStatus(**read_status(section_dir, safe_stem))


@router.get("/export")
def export(section_path: str = Query(...), stem: str = Query(...), format: str = Query("docx"), root: Path = Depends(require_dossier_root)):
    if format.lower() != "docx":
        raise HTTPException(status_code=400, detail="Only docx export is supported")
    section_dir, safe_stem = _stem_file(root, section_path, stem)
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
def export_all(format: str = Query("docx"), root: Path = Depends(require_dossier_root)):
    if format.lower() != "docx":
        raise HTTPException(status_code=400, detail="Only docx export is supported")

    docs = list_generated_docs(root)
    approved = [d for d in docs if d.get("status") == STATUS_APPROVED]
    if not approved:
        raise HTTPException(status_code=404, detail="No approved documents to export")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in approved:
            try:
                section_dir, safe_stem = _stem_file(root, doc["section_path"], doc["stem"])
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
