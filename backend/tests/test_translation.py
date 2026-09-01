"""Tests for the chunked translation service."""

import asyncio
import pytest

from app.services import translation_service, llm


def test_translate_chunks(monkeypatch):
    """A 10k‑char input should be split into 4‑chunk pieces (2500 each) and each
    chunk translated individually. The fake LLM simply upper‑cases the prompt.
    """
    text = "a" * 10000

    async def fake_generate_text(prompt: str, max_tokens=None):
        return prompt.upper()

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)

    outcome = asyncio.run(
        translation_service.translate_text(
            text, source_language="en", target_language="fr"
        )
    )
    assert outcome.text == text.upper()
    assert outcome.reason == translation_service.AI_ENGINE_NAME
    # Ensure the output length matches input (chunks joined correctly).
    assert len(outcome.text) == len(text)


def test_unsupported_language(monkeypatch):
    with pytest.raises(ValueError):
        asyncio.run(
            translation_service.translate_text(
                "test", source_language="en", target_language="de"
            )
        )
