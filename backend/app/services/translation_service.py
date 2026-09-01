"""Chunked translation service for EN/FR/PT/SW using the LLM layer.

Ported from ``regulations_translation.services.llm_translation``.
"""

from __future__ import annotations

import logging
import re
from typing import NamedTuple

from app.services import llm

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "French",
    "pt": "Portuguese",
    "sw": "Swahili",
}

class TranslationUnavailable(Exception):
    """Raised when translation could not be produced by any provider."""

class TranslationOutcome(NamedTuple):
    """Result of a translation operation.

    text: translated markdown/text
    source_language: original language code
    target_language: target language code
    reason: identifier of the engine/provider that produced the translation
    """
    text: str
    source_language: str
    target_language: str
    reason: str

AI_ENGINE_NAME = "ai-router"

SYSTEM_PROMPT = (
    "You are a professional medical and pharmaceutical regulatory translator.\n"
    "\n"
    "Translate the user's text from {source} into {target}.\n"
    "\n"
    "Rules, in order of importance:\n"
    "1. Output ONLY the translation. No preamble, no explanation, no notes, no quotation marks around the whole output, no markdown fences.\n"
    "2. Preserve exactly, without translating: drug brand names, INN (international non-proprietary) names, MedDRA terms, dosage units (mg, mL, IU), ATC codes, study and protocol identifiers, regulatory references (ICH E2D, 21 CFR 312, EU GMP Annex 11), and section numbers such as 3.2.P.1.\n"
    "3. Preserve the structure of the source: keep paragraph breaks, list markers, numbering and tabular layout as they appear.\n"
    "4. Use the register and terminology of regulatory documentation in the target language, not colloquial phrasing.\n"
    "5. If a passage is already in {target}, leave it as it is.\n"
    "6. Never add content that is not in the source, and never omit content that is. Do not summarise.\n"
    "{extra}"  # placeholder for language‑specific notes
)

# For PT and SW, add a note about preserving pharmacovigilance terminology.
EXTRA_NOTES = {
    "pt": "Note: standard pharmacovigilance/ICSR terminology may remain untranslated where that is the norm.\n",
    "sw": "Note: standard pharmacovigilance/ICSR terminology may remain untranslated where that is the norm.\n",
    "en": "",
    "fr": "",
}

# Chunk size – same as the original implementation.
CHUNK_CHARS = 2500

_PREAMBLE = re.compile(
    r"^\s*(here(?:'s| is)[^\n:]*translation[^\n:]*:|"
    r"translation[^\n:]*:|"
    r"translated text[^\n:]*:)\s*",
    re.IGNORECASE,
)

def _strip_wrapper(text: str) -> str:
    """Remove a conversational opener or markdown fence, if present."""
    cleaned = _PREAMBLE.sub("", text.strip(), count=1)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return cleaned.strip()

def chunk_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Split text into chunks no larger than *limit* characters.

    The algorithm mirrors the original implementation: prefer paragraph
    boundaries, then sentence boundaries, and finally hard‑cut if a single
    paragraph exceeds the limit.
    """
    text = text or ""
    if len(text) <= limit:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current = ""

    for para in text.split("\n\n"):
        piece = para if not current else "\n\n" + para
        if len(current) + len(piece) <= limit:
            current += piece
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(para) <= limit:
            current = para
            continue
        # Paragraph too long – split on sentence boundaries.
        sentence = ""
        for part in re.split(r"(?<=[.!?])\s+", para):
            candidate = part if not sentence else " " + part
            if len(sentence) + len(candidate) <= limit:
                sentence += candidate
                continue
            if sentence:
                chunks.append(sentence)
            # Hard cut a single long sentence.
            while len(part) > limit:
                chunks.append(part[:limit])
                part = part[limit:]
            sentence = part
        current = sentence

    if current.strip():
        chunks.append(current)

    return [c for c in chunks if c.strip()]

async def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    *,
    organization=None,
    purpose: str = "regulatory document translation",
) -> TranslationOutcome:
    """Translate *text* from ``source_language`` to ``target_language``.

    The function splits the input into chunks, translates each chunk using the
    shared LLM layer, and joins the results. If any chunk fails to produce output
    the whole operation raises :class:`TranslationUnavailable`.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported target language: {target_language}")
    if not (text or "").strip():
        raise ValueError("Nothing to translate")
    if not source_language or not target_language:
        raise ValueError("Both source and target languages are required")

    extra = EXTRA_NOTES.get(target_language, "")
    system = SYSTEM_PROMPT.format(source=source_language, target=target_language, extra=extra)
    chunks = chunk_text(text)
    logger.info(
        "Translating %s → %s (%d chars, %d chunk(s))",
        source_language,
        target_language,
        len(text),
        len(chunks),
    )

    out: list[str] = []
    for chunk in chunks:
        result = await llm.generate_text(prompt=chunk, max_tokens=None)
        if not result or not result.strip():
            raise TranslationUnavailable("Provider returned empty translation")
        out.append(_strip_wrapper(result))

    return TranslationOutcome("".join(out), source_language, target_language, AI_ENGINE_NAME)
