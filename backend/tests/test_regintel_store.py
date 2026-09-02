import os
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.regintel_store import (
    get_sources,
    ensure_sources_seeded,
    add_or_update_document,
    get_documents,
)

client = TestClient(app)

def test_seed_sources_non_empty_urls():
    ensure_sources_seeded()
    sources = get_sources()
    assert len(sources) == 5
    for src in sources:
        assert src.listing_urls
        assert all(url.startswith("http") for url in src.listing_urls)

def test_toggle_source_enabled():
    # Ensure source is enabled initially
    resp = client.get("/api/v1/regintelligence/sources")
    assert resp.status_code == 200
    data = resp.json()
    nda = next(s for s in data if s["key"] == "NDA_UG")
    assert nda["enabled"] is True
    # Toggle
    resp = client.post("/api/v1/regintelligence/sources", json={"source_key": "NDA_UG", "enabled": False})
    assert resp.status_code == 200
    # Verify
    resp = client.get("/api/v1/regintelligence/sources")
    data = resp.json()
    nda = next(s for s in data if s["key"] == "NDA_UG")
    assert nda["enabled"] is False

def test_document_dedupe_updates_last_seen():
    doc = {
        "source_key": "NDA_UG",
        "url": "http://example.com/doc1",
        "title": "Doc 1",
        "content_hash": "hash123",
        "doc_type": "regulation",
    }
    add_or_update_document(doc)
    time.sleep(0.01)
    # Add same hash again with different title
    doc2 = doc.copy()
    doc2["title"] = "Doc 1 Updated"
    add_or_update_document(doc2)
    docs = get_documents()
    assert len(docs) == 1
    entry = docs[0]
    assert entry["title"] == "Doc 1 Updated"
    first_seen = datetime.fromisoformat(entry["first_seen"])
    last_seen = datetime.fromisoformat(entry["last_seen"])
    assert last_seen > first_seen
