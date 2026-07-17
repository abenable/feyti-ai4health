"""Provider-agnostic text LLM layer — Gemini and DeepSeek side by side.

Switch with settings.LLM_PROVIDER ("gemini" | "deepseek"). Used for text
reasoning (document classification). OCR is NOT here: it needs vision, which
DeepSeek does not offer, so OCR stays on Gemini in document_processor.py.

DeepSeek is reached over its OpenAI-compatible REST API with httpx — no extra
SDK dependency.
"""

import logging

import httpx
from google.genai import types

from app.core.config import settings
from app.services.gemini_service import get_client

logger = logging.getLogger(__name__)

_DS_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


async def generate_json(prompt: str) -> str:
    """Return the model's raw response text, constrained to JSON."""
    if settings.LLM_PROVIDER == "deepseek":
        return await _deepseek(prompt, json_mode=True)
    return await _gemini(prompt, json_mode=True)


async def generate_text(prompt: str, max_tokens: int | None = None) -> str:
    """Return the model's raw response text (free-form).

    max_tokens lets long outputs (e.g. full CTD section documents) exceed the
    provider's default cap; None uses the provider default.
    """
    if settings.LLM_PROVIDER == "deepseek":
        return await _deepseek(prompt, json_mode=False, max_tokens=max_tokens)
    return await _gemini(prompt, json_mode=False, max_tokens=max_tokens)


# ── Gemini ───────────────────────────────────────────────────────────────────
async def _gemini(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else None,
        max_output_tokens=max_tokens,
    )
    resp = await get_client().aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[prompt],
        config=config,
    )
    return resp.text or ""


# ── DeepSeek (OpenAI-compatible REST) ────────────────────────────────────────
async def _deepseek(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    return await deepseek_chat(messages, json_mode=json_mode, max_tokens=max_tokens)


async def deepseek_chat(
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    """Multi-turn DeepSeek chat completion. Used by both classification (single
    prompt) and the chat interface (full message history)."""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")
    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    payload: dict = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:  # omit → provider's own max (no 512 truncation)
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}

    async with httpx.AsyncClient(timeout=_DS_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"] or ""
