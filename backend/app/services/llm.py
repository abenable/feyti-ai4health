"""Provider-agnostic text LLM layer — LiteLLM is the default; the self-hosted
Aicyclinder box and Gemini are fallbacks if it errors or is unreachable.

Used for text reasoning (document classification). OCR is NOT here: it needs
vision, which neither LiteLLM nor Aicyclinder offer, so OCR stays on Gemini in
document_processor.py.

LiteLLM (OpenAI-compatible proxy, litellm.byte10x.dev) and Aicyclinder (our
own self-hosted box, serve.py in feyti_ctd_model) both speak the OpenAI
chat-completions REST shape, so they share one _openai_chat() helper —
Aicyclinder just has no API key and no native JSON mode, so callers needing
JSON from it must ask for it in the prompt, same as generate_json()'s callers
already do for the other providers.
"""

import logging
import re

import httpx
from google.genai import types

from app.core.config import settings
from app.services.gemini_service import get_client

logger = logging.getLogger(__name__)

_LITELLM_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
# Kept well under the public gateway's own timeout (~60s) so a slow/overloaded
# box triggers the LiteLLM/Gemini fallback instead of the gateway 504ing first.
_AICYCLINDER_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def _strip_json_fence(raw: str) -> str:
    """Providers without native JSON mode (e.g. the self-hosted Aicyclinder
    base model) sometimes wrap the response in a ```json ... ``` code fence."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


async def generate_json(prompt: str) -> str:
    """Return the model's raw response text, constrained to JSON (any
    markdown code fence already stripped)."""
    raw = await _generate(prompt, json_mode=True)
    return _strip_json_fence(raw)


async def generate_text(prompt: str, max_tokens: int | None = None) -> str:
    """Return the model's raw response text (free-form).

    max_tokens lets long outputs (e.g. full CTD section documents) exceed the
    provider's default cap; None uses the provider default.
    """
    return await _generate(prompt, json_mode=False, max_tokens=max_tokens)


async def _generate(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    """LiteLLM first; Aicyclinder, then Gemini, only on failure (unreachable
    proxy, HTTP error, or a fallback's own key not configured)."""
    errors = []
    if settings.LITELLM_API_KEY:
        try:
            return await _litellm(prompt, json_mode=json_mode, max_tokens=max_tokens)
        except httpx.HTTPError as exc:
            logger.warning("[llm] LiteLLM failed, falling back to Aicyclinder: %s", exc)
            errors.append(f"litellm: {exc}")
    else:
        errors.append("litellm: LITELLM_API_KEY not set")

    try:
        return await _aicyclinder(prompt, max_tokens=max_tokens)
    except httpx.HTTPError as exc:
        logger.warning("[llm] Aicyclinder unreachable, falling back to Gemini: %s", exc)
        errors.append(f"aicyclinder: {exc}")

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


# ── LiteLLM (OpenAI-compatible proxy, litellm.byte10x.dev) ──────────────────
async def _litellm(prompt: str, json_mode: bool, max_tokens: int | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    return await litellm_chat(messages, json_mode=json_mode, max_tokens=max_tokens)


async def litellm_chat(
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    """Multi-turn LiteLLM chat completion. Used by both classification (single
    prompt) and the chat interface (full message history)."""
    if not settings.LITELLM_API_KEY:
        raise RuntimeError("LITELLM_API_KEY is not set.")
    return await _openai_chat(
        settings.LITELLM_BASE_URL, settings.LITELLM_MODEL, messages,
        settings.LITELLM_API_KEY, max_tokens, temperature, json_mode, _LITELLM_TIMEOUT,
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
