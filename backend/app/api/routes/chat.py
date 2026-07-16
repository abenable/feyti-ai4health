"""Chat backends for the demo.

Two providers, both surfaced as "Aicyclinder" to the user:
  • "aicyclinder" → the hosted fine-tuned model (Unsloth + FastAPI behind ngrok).
    The model server has no CORS headers, so we forward server-side.
  • "cloud"       → DeepSeek (kept internal; never named in the UI). A fallback
    that stays responsive when the hosted model is down.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import deepseek_chat

logger = logging.getLogger(__name__)
router = APIRouter()

# Generation on an L4 can take a while; give it room. ngrok header skips the
# free-tier browser-warning interstitial.
_TIMEOUT = httpx.Timeout(180.0, connect=10.0)
_HEADERS = {"ngrok-skip-browser-warning": "true"}

_CLOUD = "cloud"  # internal alias for DeepSeek


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.provider == _CLOUD:
        return await _chat_cloud(req)
    return await _chat_aicyclinder(req)


async def _chat_aicyclinder(req: ChatRequest) -> ChatResponse:
    url = f"{settings.AICYCLINDER_API_URL.rstrip('/')}/generate"
    payload = {
        "messages": [m.model_dump() for m in req.messages],
        "max_new_tokens": req.max_new_tokens,
        "temperature": req.temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_HEADERS)
            resp.raise_for_status()
            data = resp.json()  # ValueError if ngrok served an HTML error page
    except httpx.HTTPStatusError as exc:
        logger.error("Aicyclinder model returned %s: %s", exc.response.status_code, exc.response.text[:300])
        raise HTTPException(status_code=502, detail="The Aicyclinder model returned an error.") from exc
    except httpx.RequestError as exc:
        logger.error("Cannot reach Aicyclinder model at %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="The Aicyclinder model is offline or unreachable.") from exc
    except ValueError as exc:  # non-JSON body (e.g. ngrok "tunnel offline" page)
        logger.error("Aicyclinder model returned a non-JSON response from %s", url)
        raise HTTPException(status_code=503, detail="The Aicyclinder model is offline or unreachable.") from exc

    return ChatResponse(response=data.get("response", ""))


async def _chat_cloud(req: ChatRequest) -> ChatResponse:
    try:
        text = await deepseek_chat(
            [m.model_dump() for m in req.messages],
            max_tokens=req.max_new_tokens,
            temperature=req.temperature,
        )
    except httpx.HTTPError as exc:
        logger.error("Cloud chat provider error: %s", exc)
        raise HTTPException(status_code=502, detail="The Aicyclinder Cloud service returned an error.") from exc
    except RuntimeError as exc:  # key not configured
        logger.error("Cloud chat provider not configured: %s", exc)
        raise HTTPException(status_code=503, detail="Aicyclinder Cloud is not available.") from exc
    return ChatResponse(response=text)


@router.get("/health")
async def chat_health(provider: str = "aicyclinder"):
    """Report whether the selected backend is reachable (for the UI status badge)."""
    if provider == _CLOUD:
        if settings.DEEPSEEK_API_KEY:
            return {"status": "ok"}
        raise HTTPException(status_code=503, detail="Cloud offline")

    url = f"{settings.AICYCLINDER_API_URL.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Model offline")
