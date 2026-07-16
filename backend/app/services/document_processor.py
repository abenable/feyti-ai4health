# dossiers/document_processor.py
# ─────────────────────────────────────────────────────────────────────────────
# DocumentProcessor
#
# Extracts page-indexed text chunks from any uploaded file:
#
#   • Text PDF        → PyMuPDF  (free, instant)
#   • Scanned PDF     → PyMuPDF renders page images → Gemini vision OCR (per page)
#                       Fallback: pytesseract (if the system binary is installed)
#   • Word (.docx)    → python-docx paragraph extraction (page-estimated)
#
# Output is always a list of dicts:
#   [{"page": 1, "text": "...", "is_ocr": False}, ...]
#
# The processor also returns a flat `full_text` string (all chunks joined)
# and `had_ocr` bool for logging.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import io
import logging
import time
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# Max scanned pages to OCR (cost/time cap). The first pages carry the
# identifying content needed to classify + fill; deep pages add little.
MAX_OCR_PAGES = 12
# PyMuPDF threshold: pages with fewer chars than this are treated as scanned
SCANNED_CHAR_THRESHOLD = 50
# Total wall-clock budget for OCR of one document. Once exceeded we stop and
# use whatever text we have, so a single slow scan can't stall the request.
OCR_TOTAL_BUDGET = 90


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _page_to_png_bytes(page) -> bytes:
    """Render a PyMuPDF page to PNG bytes at 150 dpi."""
    import fitz  # PyMuPDF
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def _ocr_via_gemini_page(png_bytes: bytes) -> str:
    """
    OCR a SINGLE page image via Gemini vision, using the google-genai SDK
    (same client as gemini_service / classification_service). Per-page is far
    more reliable than batching many images in one call. Returns text or "".
    """
    try:
        from google.genai import types

        from app.services.gemini_service import get_client

        resp = get_client().models.generate_content(
            model=getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash"),
            contents=[
                types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                "Transcribe ALL text on this page of a pharmaceutical regulatory "
                "document, verbatim, preserving numbers, tables and headings. "
                "Output ONLY the transcribed text, nothing else.",
            ],
        )
        return (resp.text or "").strip()
    except Exception as exc:
        logger.warning("[OCR:Gemini] page failed: %s", exc)
        return ""


def _ocr_via_tesseract(png_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        return pytesseract.image_to_string(img)
    except Exception as exc:
        logger.warning("[OCR:Tesseract] failed: %s", exc)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# PDF extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pdf(pdf_bytes: bytes) -> Tuple[List[dict], bool]:
    """
    Extract page chunks from a PDF.
    Returns (chunks, had_ocr).
    chunks = [{"page": n, "text": "...", "is_ocr": bool}]
    """
    try:
        import fitz
    except ImportError:
        import pymupdf as fitz  # type: ignore

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks: List[dict] = []
    scanned_pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if len(text) >= SCANNED_CHAR_THRESHOLD:
            chunks.append({"page": page_num + 1, "text": text, "is_ocr": False})
        else:
            scanned_pages.append((page_num + 1, page))

    had_ocr = False
    diag: List[str] = []

    if scanned_pages:
        if len(scanned_pages) > MAX_OCR_PAGES:
            logger.info(
                "[Processor] %d scanned pages — capping at %d",
                len(scanned_pages), MAX_OCR_PAGES,
            )
            scanned_pages = scanned_pages[:MAX_OCR_PAGES]

        logger.info("[Processor] Running OCR on %d scanned page(s)", len(scanned_pages))

        # Per-page OCR — Gemini per page (reliable verbatim), with tesseract as a
        # per-page fallback when Gemini returns thin text. Per-page avoids the flaky
        # batch behaviour and degrades gracefully page by page.
        _start = time.monotonic()
        gem_chars = 0
        tess_chars = 0
        for page_num, page in scanned_pages:
            if time.monotonic() - _start > OCR_TOTAL_BUDGET:
                diag.append(f"OCR stopped at budget after page {page_num}")
                break
            png = _page_to_png_bytes(page)
            text = _ocr_via_gemini_page(png)
            if text:
                gem_chars += len(text)
            # A real page has hundreds of chars; if Gemini returns thin text
            # (a summary/refusal), fall back to tesseract and keep the longer.
            if len(text) < 100:
                t = _ocr_via_tesseract(png)
                if len(t) > len(text):
                    text = t
                    tess_chars += len(t)
            chunks.append({"page": page_num, "text": text, "is_ocr": True})
        had_ocr = True
        diag.append(f"Gemini/page: {gem_chars} chars; Tesseract: {tess_chars} chars")
        logger.info("[Processor] per-page OCR: gemini=%d tesseract=%d chars",
                    gem_chars, tess_chars)

    # Sort by page number
    chunks.sort(key=lambda c: c["page"])
    return chunks, had_ocr, "; ".join(diag)


# ─────────────────────────────────────────────────────────────────────────────
# Word extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_docx(file_bytes: bytes) -> List[dict]:
    """
    Extract text from a Word document.
    Word has no native pages — we estimate page breaks every ~45 paragraphs.
    Returns chunks with estimated page numbers.
    """
    from docx import Document  # python-docx

    doc = Document(io.BytesIO(file_bytes))
    chunks: List[dict] = []
    PARAS_PER_PAGE = 45

    page_num = 1
    buffer: List[str] = []

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            buffer.append(text)
        if len(buffer) >= PARAS_PER_PAGE:
            chunks.append({"page": page_num, "text": "\n".join(buffer), "is_ocr": False})
            buffer = []
            page_num += 1

    if buffer:
        chunks.append({"page": page_num, "text": "\n".join(buffer), "is_ocr": False})

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

class DocumentProcessor:
    """
    Extract text chunks from an uploaded file.

    Usage
    -----
        processor = DocumentProcessor()
        result = processor.process(file_bytes=b"...", filename="report.pdf")
        result.chunks      # [{page, text, is_ocr}]
        result.full_text   # all text joined
        result.had_ocr     # True if any page needed OCR
        result.error       # non-None if extraction failed
    """

    class Result:
        def __init__(self, chunks, had_ocr=False, error=None, ocr_diag=""):
            self.chunks: List[dict] = chunks
            self.had_ocr: bool = had_ocr
            self.error: str | None = error
            self.ocr_diag: str = ocr_diag

        @property
        def full_text(self) -> str:
            return "\n\n".join(c["text"] for c in self.chunks if c.get("text"))

        @property
        def page_count(self) -> int:
            return len(self.chunks)

    def process(self, file_bytes: bytes, filename: str) -> "DocumentProcessor.Result":
        fname = (filename or "").lower()
        t0 = time.time()

        try:
            ocr_diag = ""
            if fname.endswith(".docx") or fname.endswith(".doc"):
                chunks = _extract_docx(file_bytes)
                had_ocr = False
            elif fname.endswith(".pdf"):
                chunks, had_ocr, ocr_diag = _extract_pdf(file_bytes)
            else:
                # Attempt PDF parse for unknown extensions (many regulatory docs
                # are sent without extension or with wrong extension)
                try:
                    chunks, had_ocr, ocr_diag = _extract_pdf(file_bytes)
                except Exception:
                    return self.Result([], error=f"Unsupported file type: {filename}")

            elapsed = time.time() - t0
            logger.info(
                "[Processor] %s → %d pages, %d chars, OCR=%s [%s] (%.1fs)",
                filename, len(chunks),
                sum(len(c["text"]) for c in chunks),
                had_ocr, ocr_diag, elapsed,
            )
            return self.Result(chunks, had_ocr=had_ocr, ocr_diag=ocr_diag)

        except Exception as exc:
            logger.exception("[Processor] Failed to process '%s': %s", filename, exc)
            return self.Result([], error=str(exc))
