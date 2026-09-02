"""Chat backends for the demo.

Two providers, both surfaced as "Aicyclinder" to the user:
  • "aicyclinder" → the self-hosted base model (unsloth/Qwen3.8-27B, LoRA
    disabled server-side — the CTD-classifier adapter only emits section
    codes, not conversation). The default; requests to it that fail
    (box unreachable, HTTP error) fall back to "cloud" automatically.
  • "cloud"       → LiteLLM (kept internal; never named in the UI).
"""

import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_dossier_root
from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.dossier_service import (
    context_block,
    list_generated_docs,
    read_generated,
    read_meta,
    _resolve_section_dir,
    _safe_filename,
)
from app.services.llm import aicyclinder_chat, litellm_chat

logger = logging.getLogger(__name__)
router = APIRouter()

_CLOUD = "cloud"  # internal alias for LiteLLM


def _dossier_system_prompt(root: Path, section_path: str | None, stem: str | None) -> str | None:
    """Ground the assistant in the dossier: product context, what's been filed,
    and (if chat was opened from a document) that document's current draft.
    No vector store — one dossier is a few hundred KB of markdown.
    ponytail: full-text injection; move to embeddings if a real dossier
    overflows the context window.
    """
    parts = [context_block(root, "PRODUCT CONTEXT:")]

    docs = list_generated_docs(root)
    if docs:
        lines = [f"- {d['ctd_path']} {d['title']} [{d['status']}]" for d in docs[:60]]
        parts.append("FILED CTD SECTIONS:\n" + "\n".join(lines))

    if section_path and stem:
        try:
            section_dir = _resolve_section_dir(root, section_path)
            safe_stem = _safe_filename(stem)
            meta = read_meta(section_dir, safe_stem)
            markdown = read_generated(section_dir, safe_stem)
            if meta and markdown:
                parts.append(
                    f"USER IS CURRENTLY VIEWING: {meta.get('section_path', '')} "
                    f"{meta.get('title', '')}\nCurrent draft:\n---\n{markdown[:4000]}\n---"
                )
        except ValueError:
            pass  # bad path from the client; fall back to dossier-wide context only

    parts = [p for p in parts if p]
    if not parts:
        return None
    return (
        "You are Aicyclinder, an assistant embedded in a CTD regulatory dossier "
        "tool. Use the following dossier state to answer questions; do not "
        "invent product, quality, safety, or efficacy facts beyond it.\n\n"
        + "\n\n".join(parts)
    )


def _with_system_prompt(req: ChatRequest, root: Path) -> list[dict]:
    messages = [m.model_dump() for m in req.messages]
    system_prompt = _dossier_system_prompt(root, req.section_path, req.stem)
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    return messages


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, root: Path = Depends(require_dossier_root)):
    if req.provider == _CLOUD:
        return await _chat_cloud(req, root)
    return await _chat_aicyclinder(req, root)


async def _chat_aicyclinder(req: ChatRequest, root: Path) -> ChatResponse:
    try:
        text = await aicyclinder_chat(
            _with_system_prompt(req, root),
            max_tokens=req.max_new_tokens,
            temperature=req.temperature,
        )
    except httpx.HTTPError as exc:
        logger.warning("Aicyclinder unreachable, falling back to LiteLLM: %s", exc)
        return await _chat_cloud(req, root)
    return ChatResponse(response=text)


async def _chat_cloud(req: ChatRequest, root: Path) -> ChatResponse:
    try:
        text = await litellm_chat(
            _with_system_prompt(req, root),
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
async def chat_health(dossier_id: str, provider: str = "aicyclinder"):
    """Report whether the selected backend is reachable (for the UI status badge).
    Provider health doesn't depend on dossier content; dossier_id is only here
    because it's part of this route's URL prefix."""
    if provider == _CLOUD:
        if settings.LITELLM_API_KEY:
            return {"status": "ok"}
        raise HTTPException(status_code=503, detail="Cloud offline")

    url = f"{settings.FEYTI_CTD_API_URL.rstrip('/')}/ping"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Model offline")
