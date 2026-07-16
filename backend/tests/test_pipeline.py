"""Load-bearing checks for extraction, classification, and dossier filing."""

import json

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


async def test_classify_hallucination_guard(monkeypatch):
    from app.services import classification_service

    # Patch the provider layer so the test needs no network / API key, and is
    # independent of whether LLM_PROVIDER is gemini or deepseek.
    async def fake_generate_json(prompt: str) -> str:
        return json.dumps({"section_path": "9.9.9", "confidence": 0.9})

    monkeypatch.setattr(classification_service, "generate_json", fake_generate_json)

    result = await classification_service.classify("some text")
    # Hallucinated path should fall back to 1.2 Product Information.
    assert result["section_path"] == "1.2"
    assert result["confidence"] == 0.0
    assert result["module"] == "Module 1 — Administrative"


async def test_classify_normalizes_path_with_title(monkeypatch):
    """Models (esp. DeepSeek) echo 'path: title' — must resolve to the bare path."""
    from app.services import classification_service

    async def fake_generate_json(prompt: str) -> str:
        return json.dumps(
            {"section_path": "3.2.P.8.3: Stability Data (Drug Product)", "confidence": 0.95}
        )

    monkeypatch.setattr(classification_service, "generate_json", fake_generate_json)

    result = await classification_service.classify("stability report")
    assert result["section_path"] == "3.2.P.8.3"
    assert result["confidence"] == 0.95
    assert result["module"] == "Module 3 — Quality"


def test_file_into_dossier_rejects_path_traversal(monkeypatch, tmp_path):
    from app.services import dossier_service

    monkeypatch.setattr(dossier_service, "_ROOT", tmp_path)
    classification = {
        "section_path": "3.2.P.8.1",
        "title": "Stability Summary and Conclusion (Drug Product)",
        "module": "Module 3 — Quality",
        "confidence": 0.85,
    }
    dossier_service.file_into_dossier(
        b"payload", "../evil.pdf", classification, "extracted text"
    )
    written = list(tmp_path.rglob("*.pdf"))
    assert len(written) == 1
    assert written[0].name == "evil.pdf"
    assert written[0].resolve().is_relative_to(tmp_path.resolve())


def test_tree_after_one_placement(monkeypatch, tmp_path):
    from app.services import dossier_service

    monkeypatch.setattr(dossier_service, "_ROOT", tmp_path)
    classification = {
        "section_path": "3.2.P.8.1",
        "title": "Stability Summary and Conclusion (Drug Product)",
        "module": "Module 3 — Quality",
        "confidence": 0.85,
    }
    dossier_service.file_into_dossier(
        b"payload", "stability.pdf", classification, "extracted text"
    )
    tree = dossier_service.tree()
    assert len(tree) == 1
    assert tree[0]["module"] == "Module 3 — Quality"
    assert len(tree[0]["sections"]) == 1
    section = tree[0]["sections"][0]
    assert section["section_path"] == "3.2.P.8.1"
    assert len(section["documents"]) == 1
    assert section["documents"][0]["name"] == "stability.pdf"
