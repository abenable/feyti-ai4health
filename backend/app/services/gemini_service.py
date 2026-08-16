from google import genai

from app.core.config import settings

_client: genai.Client | None = None


def get_client() -> genai.Client:
    # Cached singleton: a fresh Client per call gets GC-closed when the result
    # is chained (get_client().models...), raising "client has been closed".
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client
