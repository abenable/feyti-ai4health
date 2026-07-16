from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import DocumentAnalysisError
from app.services.document_parser import extract_text_from_docx


_client: genai.Client | None = None


def get_client() -> genai.Client:
    # Cached singleton: a fresh Client per call gets GC-closed when the result
    # is chained (get_client().models...), raising "client has been closed".
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


async def analyze_document(
    file_bytes: bytes,
    mime_type: str,
    prompt: str = "Please summarize the following document:",
) -> str:
    """Sends document content to Gemini for analysis."""
    contents = []

    if mime_type == "application/pdf":
        contents.append(
            types.Part.from_bytes(data=file_bytes, mime_type="application/pdf")
        )
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        text_content = extract_text_from_docx(file_bytes)
        contents.append(text_content)
    else:
        raise DocumentAnalysisError(f"Unsupported file type: {mime_type}", 415)

    contents.append(prompt)

    try:
        response = await get_client().aio.models.generate_content(
            model=settings.GEMINI_MODEL, contents=contents
        )
    except Exception as exc:
        raise DocumentAnalysisError(
            "The AI service request failed. Please try again."
        ) from exc

    if not response.text:
        raise DocumentAnalysisError(
            "The AI service returned an empty response. Please try again."
        )

    return response.text
