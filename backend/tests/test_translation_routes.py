"""Integration tests for the translation API endpoints."""

import json
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from main import app  # Import the FastAPI app
from app.core import config
from app.services.dossier_service import create_dossier, create_section_document, write_generated, dossier_root
from app.models.schemas import TranslationRequest


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Point the application to a temporary dossiers root.
    monkeypatch.setattr(config.settings, "DOSSIERS_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_translation_flow(client, monkeypatch):
    # Create a dossier via the service.
    dossier = create_dossier("test")
    dossier_id = dossier["id"]
    root_path = dossier_root(dossier_id)
    # Use the service to create a section and write original markdown.
    section = create_section_document(
        root=root_path,
        ctd_path="3.2.P.8.1",
        title="Stability",
        module="Module 3 — Quality",
        stem="section1",
    )
    # The function returns dict with section_dir, stem, section_path
    section_dir = section["section_dir"]
    stem = section["stem"]
    # Write original generated markdown.
    write_generated(section_dir, stem, "original content", status="draft")

    # Mock the translation service to return a predictable outcome.
    async def fake_translate_text(text, source_language, target_language, **kwargs):
        class Outcome:
            def __init__(self, text):
                self.text = f"{text.upper()} ({target_language})"
                self.reason = "fake"
        return Outcome(text)

    import app.services.translation_service as ts_mod
    monkeypatch.setattr(ts_mod, "translate_text", fake_translate_text)

    # POST translation request.
    # Build the section_path using the same sanitisation as the service.
    from app.services.dossier_service import _safe_dir_name
    safe_module = _safe_dir_name("Module 3 — Quality")
    safe_section = _safe_dir_name("3.2.P.8.1 Stability")
    payload = {
        "target_language": "fr",
        "section_path": f"{safe_module}/{safe_section}",
        "stem": stem,
    }
    response = client.post(f"/api/v1/dossiers/{dossier_id}/translate/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["stem"] == stem
    assert data["language"] == "fr"
    # Verify the translation is stored on the document row.
    from app.services import db_repo
    row = db_repo.get_document_row(*db_repo.doc_key(section_dir, stem))
    assert row.translations["fr"].endswith("(fr)")

    # GET status should list available languages.
    status_resp = client.get(
        f"/api/v1/dossiers/{dossier_id}/translate/status",
        params={"section_path": f"{safe_module}/{safe_section}"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert any(item["stem"] == stem and "fr" in item["available"] for item in status_data)
