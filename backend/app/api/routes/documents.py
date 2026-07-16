import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from app.core.exceptions import DocumentAnalysisError
from app.services.gemini_service import analyze_document
from app.services.document_processor import DocumentProcessor
from app.services.classification_service import classify
from app.services.dossier_service import file_into_dossier
from app.models.schemas import AnalysisResponse, ProcessResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def extract(file_bytes: bytes, mime_type: str, filename: str) -> tuple[str, bool]:
    """Extract full text from a PDF or DOCX and report whether OCR was used."""
    result = DocumentProcessor().process(file_bytes, filename)
    if result.error:
        raise HTTPException(status_code=422, detail=result.error)
    return result.full_text, result.had_ocr

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB limit for Gemini
DEFAULT_PROMPT = "Please summarize this document comprehensively."

@router.post("/analyze", response_model=AnalysisResponse)
async def upload_and_analyze(
    file: UploadFile = File(...),
    prompt: str = Form(DEFAULT_PROMPT)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Please upload a PDF or DOCX file."
        )

    try:
        file_bytes = await file.read()
        normalized_prompt = prompt.strip() or DEFAULT_PROMPT
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
            
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum allowed size is 15MB. (Your file: {len(file_bytes) // (1024*1024)}MB)"
            )
        
        logger.info(
            "Analyzing %s (%s bytes) with prompt length %s",
            file.filename,
            len(file_bytes),
            len(normalized_prompt),
        )

        summary = await analyze_document(
            file_bytes=file_bytes,
            mime_type=file.content_type,
            prompt=normalized_prompt,
        )

        logger.info("Successfully analyzed %s", file.filename)

        return AnalysisResponse(
            summary=summary,
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(file_bytes)
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise
    except ValueError as exc:
        logger.warning("Validation error during analysis: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DocumentAnalysisError as exc:
        logger.error("Analysis failed for %s: %s", file.filename, exc.message, exc_info=True)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error("Unexpected analysis failure for %s", file.filename, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Failed to analyze document with the AI service.",
        ) from exc
    finally:
        await file.close()


@router.post("/process", response_model=ProcessResponse)
async def process(file: UploadFile = File(...)):
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

    text, ocr_used = extract(file_bytes, file.content_type, file.filename)
    classification = await classify(text)
    placed = file_into_dossier(file_bytes, file.filename, classification, text)

    return ProcessResponse(
        filename=file.filename,
        extracted_chars=len(text),
        ocr_used=ocr_used,
        classification=classification,
        dossier_folder=placed["folder"],
    )
