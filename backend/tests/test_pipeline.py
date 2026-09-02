"""Load-bearing checks for extraction, classification, and dossier filing."""

import json

import httpx
import pytest


def _tiny_text_pdf_bytes(
    text: str = "This is a stability study protocol document used for testing the Feyti regulatory pipeline.",
) -> bytes:
    import io

    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_extract_text_pdf_no_ocr():
    from app.services.document_processor import DocumentProcessor

    pdf_bytes = _tiny_text_pdf_bytes()
    result = DocumentProcessor().process(pdf_bytes, "report.pdf")
    assert "stability" in result.full_text.lower()
    assert result.had_ocr is False


pytestmark = pytest.mark.anyio


async def _fake_classify_section_offline(text: str) -> str | None:
    """Simulates the fine-tuned classifier being unreachable, so these tests
    exercise the LLM fallback path (hallucination guard, normalization)."""
    return None


async def test_generate_json_strips_markdown_fence(monkeypatch):
    """Providers without native JSON mode (the self-hosted base model) can
    wrap the response in ```json ... ``` -- generate_json must still return
    clean JSON, for every caller (classification, extraction, ...)."""
    from app.services import llm

    async def fake_aicyclinder(prompt, max_tokens=None):
        return '```json\n{"section_path": "3.2.P.8.3", "confidence": 0.95}\n```'

    monkeypatch.setattr(llm, "_aicyclinder", fake_aicyclinder)

    raw = await llm.generate_json("prompt")
    assert raw == '{"section_path": "3.2.P.8.3", "confidence": 0.95}'


async def test_classify_hallucination_guard(monkeypatch, tmp_path):
    from app.services import classification_service

    # Patch the provider layer so the test needs no network / API key,
    # independent of the llm.py fallback chain's provider order.
    async def fake_generate_json(prompt: str) -> str:
        return json.dumps({"section_path": "9.9.9", "confidence": 0.9})

    monkeypatch.setattr(classification_service, "generate_json", fake_generate_json)
    monkeypatch.setattr(classification_service, "_classify_section", _fake_classify_section_offline)

    result = await classification_service.classify("some text", tmp_path)
    # Hallucinated path should fall back to 1.2 Product Information.
    assert result["section_path"] == "1.2"
    assert result["confidence"] == 0.0
    assert result["module"] == "Module 1 — Administrative"


async def test_classify_normalizes_path_with_title(monkeypatch, tmp_path):
    """Some providers echo 'path: title' — must resolve to the bare path."""
    from app.services import classification_service

    async def fake_generate_json(prompt: str) -> str:
        return json.dumps(
            {"section_path": "3.2.P.8.3: Stability Data (Drug Product)", "confidence": 0.95}
        )

    monkeypatch.setattr(classification_service, "generate_json", fake_generate_json)
    monkeypatch.setattr(classification_service, "_classify_section", _fake_classify_section_offline)

    result = await classification_service.classify("stability report", tmp_path)
    assert result["section_path"] == "3.2.P.8.3"
    assert result["confidence"] == 0.95
    assert result["module"] == "Module 3 — Quality"


async def test_classify_uses_finetuned_model_when_reachable(monkeypatch, tmp_path):
    """When the specialist classifier is reachable, its section_path is
    authoritative even if the LLM's own JSON guess disagrees."""
    from app.services import classification_service

    async def fake_classify_section(text: str) -> str:
        return "3.2.P.8.3"

    async def fake_generate_json(prompt: str) -> str:
        # LLM disagrees on section_path but that's fine — only its
        # justification/summary/key_points should be used.
        return json.dumps(
            {
                "section_path": "1.2",
                "confidence": 0.5,
                "justification": "Discusses long-term stability testing.",
                "summary": "Stability data summary.",
                "key_points": ["24-month long-term data"],
            }
        )

    monkeypatch.setattr(classification_service, "_classify_section", fake_classify_section)
    monkeypatch.setattr(classification_service, "generate_json", fake_generate_json)

    result = await classification_service.classify("stability report", tmp_path)
    assert result["section_path"] == "3.2.P.8.3"
    assert result["confidence"] == 1.0
    assert result["module"] == "Module 3 — Quality"
    assert result["justification"] == "Discusses long-term stability testing."
    assert result["key_points"] == ["24-month long-term data"]


def test_file_into_dossier_rejects_path_traversal(tmp_path):
    from app.services import db_repo, dossier_service

    classification = {
        "section_path": "3.2.P.8.1",
        "title": "Stability Summary and Conclusion (Drug Product)",
        "module": "Module 3 — Quality",
        "confidence": 0.85,
    }
    dossier_service.file_into_dossier(
        tmp_path, b"payload", "../evil.pdf", classification, "extracted text"
    )
    # The filename is basename-sanitized and the row stays inside the dossier.
    docs = db_repo.list_documents(db_repo.dossier_id_from_root(tmp_path))
    assert len(docs) == 1
    assert docs[0].filename == "evil.pdf"
    assert ".." not in docs[0].section_path and "/" not in docs[0].filename


async def test_llm_falls_back_aicyclinder_to_litellm_to_gemini(monkeypatch):
    """Aicyclinder is tried first; only on failure does it try LiteLLM (if
    configured), then Gemini."""
    from app.core.config import settings
    from app.services import llm

    async def failing_aicyclinder(prompt, max_tokens=None):
        raise httpx.ConnectError("self-hosted box unreachable")

    async def failing_litellm(prompt, json_mode, max_tokens=None):
        raise httpx.HTTPStatusError("suspended", request=None, response=httpx.Response(429))

    async def fake_gemini(prompt, json_mode, max_tokens=None):
        return "gemini response"

    monkeypatch.setattr(settings, "LITELLM_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_aicyclinder", failing_aicyclinder)
    monkeypatch.setattr(llm, "_litellm", failing_litellm)
    monkeypatch.setattr(llm, "_gemini", fake_gemini)

    result = await llm.generate_text("prompt")
    assert result == "gemini response"


async def test_llm_prefers_aicyclinder_when_reachable(monkeypatch):
    from app.services import llm

    async def fake_aicyclinder(prompt, max_tokens=None):
        return "aicyclinder response"

    async def unreachable_litellm(*args, **kwargs):
        raise AssertionError("should not fall back when aicyclinder succeeds")

    monkeypatch.setattr(llm, "_aicyclinder", fake_aicyclinder)
    monkeypatch.setattr(llm, "_litellm", unreachable_litellm)

    result = await llm.generate_text("prompt")
    assert result == "aicyclinder response"


def test_tree_after_one_placement(tmp_path):
    from app.services import dossier_service

    classification = {
        "section_path": "3.2.P.8.1",
        "title": "Stability Summary and Conclusion (Drug Product)",
        "module": "Module 3 — Quality",
        "confidence": 0.85,
    }
    dossier_service.file_into_dossier(
        tmp_path, b"payload", "stability.pdf", classification, "extracted text"
    )
    tree = dossier_service.tree(tmp_path)
    assert len(tree) == 1
    assert tree[0]["module"] == "Module 3 — Quality"
    assert len(tree[0]["sections"]) == 1
    section = tree[0]["sections"][0]
    assert section["section_path"] == "3.2.P.8.1"
    assert len(section["documents"]) == 1
    assert section["documents"][0]["name"] == "stability.pdf"
