"""Provider-agnostic text LLM layer — self-hosted Aicyclinder is the default,
Kimi and Gemini are fallbacks if it errors or is unreachable.

Used for text reasoning (document classification). OCR is NOT here: it needs
vision, which neither Kimi nor Aicyclinder offer, so OCR stays on Gemini in
document_processor.py.

Kimi (Moonshot AI) and Aicyclinder (our own self-hosted box, serve.py in
feyti_ctd_model) both speak the OpenAI chat-completions REST shape, so they
share one _openai_chat() helper — Aicyclinder just has no API key and no
native JSON mode, so callers needing JSON from it must ask for it in the
prompt, same as generate_json()'s callers already do for the other providers.
"""

import logging

import httpx
from google.genai import types

from app.core.config import settings
from app.services.gemini_service import get_client

logger = logging.getLogger(__name__)

_KIMI_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_AICYCLINDER_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


async def generate_json(prompt: str) -> str:
    """Return the model's raw response text, constrained to JSON."""
    return await _generate(prompt, json_mode=True)


async def generate_text(prompt: str, max_tokens: int | None = None) -> str:
    """Return the model's raw response text (free-form).

    max_tokens lets long outputs (e.g. full CTD section documents) exceed the
    provider's default cap; None uses the provider default.
    """
    return await _generate(prompt, json_mode=False, max_tokens=max_tokens)


async def _generate(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    """Self-hosted first; Kimi, then Gemini, only on failure (unreachable box,
    HTTP error, or the fallback's own key not configured)."""
    errors = []
    try:
        return await _aicyclinder(prompt, max_tokens=max_tokens)
    except httpx.HTTPError as exc:
        logger.warning("[llm] Aicyclinder unreachable, falling back to Kimi: %s", exc)
        errors.append(f"aicyclinder: {exc}")

    if settings.KIMI_API_KEY:
        try:
            return await _kimi(prompt, json_mode=json_mode, max_tokens=max_tokens)
        except httpx.HTTPError as exc:
            logger.warning("[llm] Kimi failed, falling back to Gemini: %s", exc)
            errors.append(f"kimi: {exc}")

    try:
        return await _gemini(prompt, json_mode=json_mode, max_tokens=max_tokens)
    except Exception as exc:
        errors.append(f"gemini: {exc}")
        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}") from exc


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


# ── Shared OpenAI-compatible REST call ──────────────────────────────────────
async def _openai_chat(
    base_url: str,
    model: str,
    messages: list[dict],
    api_key: str | None,
    max_tokens: int | None,
    temperature: float,
    json_mode: bool,
    timeout: httpx.Timeout,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:  # omit → provider's own max (no 512 truncation)
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


# ── Kimi / Moonshot AI ───────────────────────────────────────────────────────
async def _kimi(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    return await kimi_chat(messages, json_mode=json_mode, max_tokens=max_tokens)


async def kimi_chat(
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    """Multi-turn Kimi chat completion. Used by both classification (single
    prompt) and the chat interface (full message history)."""
    if not settings.KIMI_API_KEY:
        raise RuntimeError("KIMI_API_KEY is not set.")
    return await _openai_chat(
        settings.KIMI_BASE_URL, settings.KIMI_MODEL, messages,
        settings.KIMI_API_KEY, max_tokens, temperature, json_mode, _KIMI_TIMEOUT,
    )


# ── Aicyclinder (self-hosted, GPU EC2 box) ──────────────────────────────────
async def _aicyclinder(prompt: str, max_tokens: int | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    return await aicyclinder_chat(messages, max_tokens=max_tokens)


async def aicyclinder_chat(
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float = 0.0,
) -> str:
    """Multi-turn chat against the self-hosted base model (LoRA disabled
    server-side, see serve.py's /v1/chat/completions). No API key, no native
    JSON mode."""
    return await _openai_chat(
        f"{settings.FEYTI_CTD_API_URL.rstrip('/')}/v1", "aicyclinder-base", messages,
        None, max_tokens, temperature, json_mode=False, timeout=_AICYCLINDER_TIMEOUT,
    )
