import io
from docx import Document


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from a DOCX file byte stream."""
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(
            "The DOCX file could not be read. It may be corrupted or invalid."
        ) from exc

    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())

    if not full_text:
        raise ValueError("The DOCX file does not contain any readable text.")

    return "\n".join(full_text)
