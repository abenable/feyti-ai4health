import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.api.deps import require_dossier_root
from app.services.document_processor import DocumentProcessor
from app.services.classification_service import classify
from app.services.extraction_service import extract_fields
from app.services.dossier_service import file_into_dossier, write_generated, write_fields
from app.services.generation_service import generate_document
from app.models.schemas import ProcessResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def extract(file_bytes: bytes, mime_type: str, filename: str) -> tuple[str, bool, list[dict]]:
    """Extract full text + page chunks from a PDF or DOCX; report whether OCR was used."""
    result = DocumentProcessor().process(file_bytes, filename)
    if result.error:
        raise HTTPException(status_code=422, detail=result.error)
    return result.full_text, result.had_ocr, result.chunks

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB limit for Gemini


@router.post("/process", response_model=ProcessResponse)
async def process(file: UploadFile = File(...), root: Path = Depends(require_dossier_root)):
    """Run extraction, classification, and file into the dossier."""
    if not file:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Please upload a PDF or DOCX file.",
        )

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 15MB. (Your file: {len(file_bytes) // (1024 * 1024)}MB)",
        )

    text, ocr_used, chunks = extract(file_bytes, file.content_type, file.filename)
    classification = await classify(text, root)  # includes summary + key_points
    placed = file_into_dossier(root, file_bytes, file.filename, classification, text, chunks)

    # Information extraction: a failure here must not sink the whole upload.
    fields: list[dict] = []
    try:
        fields = await extract_fields(text, classification, root)
        write_fields(placed["section_dir"], placed["stem"], fields)
    except Exception as exc:
        logger.warning("Field extraction failed for %s: %s", file.filename, exc)

    # Auto-generate the initial CTD section draft for review.
    try:
        draft = await generate_document(text, classification, root)
        write_generated(placed["section_dir"], placed["stem"], draft, status="draft")
    except Exception as exc:
        logger.warning("Auto-generation failed for %s: %s", file.filename, exc)

    return ProcessResponse(
        filename=file.filename,
        extracted_chars=len(text),
        ocr_used=ocr_used,
        classification=classification,
        summary=classification.get("summary", ""),
        key_points=classification.get("key_points", []),
        fields=fields,
        dossier_folder=placed["folder"],
        section_path=placed["folder_path"],
        stem=placed["stem"],
    )
