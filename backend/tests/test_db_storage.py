"""Tests for the PostgreSQL-backed storage layer (Dossier/Document/FeatureRecord)."""

import pytest


def test_document_roundtrip_and_upsert():
    from app.services import db_repo

    db_repo.ensure_dossier_row("d1", name="Dossier One")
    section_dir = db_repo.section_handle("/roots/d1", "Module 3 — Quality", "3.2.P.8.1 Stability")
    dossier_id, section_path, stem = db_repo.doc_key(section_dir, "rep.pdf")
    assert dossier_id == "d1"
    assert section_path == "Module 3 — Quality/3.2.P.8.1 Stability"

    db_repo.upsert_document(
        dossier_id, section_path, stem,
        filename="rep.pdf", original_data=b"pdf-bytes", extracted_text="text",
        meta={"filename": "rep.pdf", "stem": stem}, status="draft",
    )
    row = db_repo.get_document_row(dossier_id, section_path, stem)
    assert row.original_data == b"pdf-bytes"
    assert row.meta["stem"] == stem

    # Upserting the same key replaces the row instead of duplicating it.
    db_repo.upsert_document(
        dossier_id, section_path, stem,
        filename="rep.pdf", generated_markdown="# Draft", status="edited",
    )
    rows = [r for r in db_repo.list_documents(dossier_id) if r.stem == stem]
    assert len(rows) == 1
    assert rows[0].generated_markdown == "# Draft"
    assert rows[0].status == "edited"


def test_update_document_fields_patches_json_columns():
    from app.services import db_repo

    db_repo.upsert_document("d2", "Mod/Sec", "s1", meta={"a": 1}, translations={"en": "x"})
    row = db_repo.update_document_fields(
        "d2", "Mod/Sec", "s1",
        meta_patch={"b": 2}, translations_patch={"fr": "y"}, status="approved",
    )
    assert row.meta == {"a": 1, "b": 2}
    assert row.translations == {"en": "x", "fr": "y"}
    assert row.status == "approved"
    assert db_repo.update_document_fields("d2", "Mod/Sec", "missing") is None


def test_feature_record_upsert_and_list():
    from app.services import db_repo

    db_repo.feature_put("scope1", "pv_report", "r1", {"report_id": "r1", "v": 1})
    db_repo.feature_put("scope1", "pv_report", "r2", {"report_id": "r2"})
    db_repo.feature_put("scope1", "pv_report", "r1", {"report_id": "r1", "v": 2})

    rows = db_repo.feature_list("scope1", "pv_report")
    assert [r.record_key for r in rows] == ["r1", "r2"]
    assert rows[0].data["v"] == 2
    assert db_repo.feature_get("scope1", "pv_report", "r1").data["v"] == 2
    assert db_repo.feature_exists("scope1", "pv_report")
    assert not db_repo.feature_exists("scope1", "literature_search")


def test_unique_slug_dedupes():
    from app.services import db_repo

    db_repo.ensure_dossier_row("thing", name="Thing")
    assert db_repo.unique_slug("thing") == "thing-2"
    db_repo.ensure_dossier_row("thing-2", name="Thing 2")
    assert db_repo.unique_slug("thing") == "thing-3"
    assert db_repo.unique_slug("other") == "other"


def test_original_bytes_served_from_document_row():
    from fastapi.testclient import TestClient

    from main import app
    from app.services import db_repo, dossier_service

    client = TestClient(app)
    created = client.post("/api/v1/dossiers", json={"name": "Bytes Dossier"})
    assert created.status_code == 200
    dossier_id = created.json()["id"]
    root = dossier_service.dossier_root(dossier_id)

    placement = dossier_service.file_into_dossier(
        root, b"%PDF-fake", "source.pdf",
        {
            "section_path": "3.2.P.8.1",
            "title": "Stability Summary and Conclusion (Drug Product)",
            "module": "Module 3 — Quality",
            "confidence": 0.9,
        },
        "extracted",
    )
    resp = client.get(
        f"/api/v1/dossiers/{dossier_id}/original",
        params={"section_path": placement["folder_path"], "stem": placement["stem"]},
    )
    assert resp.status_code == 200
    assert resp.content == b"%PDF-fake"
    assert resp.headers["content-type"] == "application/pdf"

    # Authored documents (no source file) 404.
    info = dossier_service.create_section_document(
        root, ctd_path="1.2", title="Product Information", module="Module 1 — Administrative",
    )
    resp = client.get(
        f"/api/v1/dossiers/{dossier_id}/original",
        params={"section_path": info["section_path"], "stem": info["stem"]},
    )
    assert resp.status_code == 404
