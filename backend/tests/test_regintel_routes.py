import pytest
from fastapi.testclient import TestClient
from main import app
from app.services import db_repo
from app.services.regintel_store import get_alerts

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_store():
    # Fresh DB per test (conftest); sources are re-seeded there.
    from app.services.regintel_store import ensure_sources_seeded
    ensure_sources_seeded()
    yield

def test_dashboard_returns_collections():
    resp = client.get("/api/v1/regintelligence/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["alerts", "changes", "deadlines", "sources", "stats"]:
        assert key in data
    # collections should be lists
    assert isinstance(data["alerts"], list)
    assert isinstance(data["sources"], list)

def test_create_deadline():
    payload = {
        "title": "Test Deadline",
        "due_date": "2099-12-31",
        "source": "manual",
    }
    resp = client.post("/api/v1/regintelligence/deadlines", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["due_date"] == payload["due_date"]
    assert data["source"] == payload["source"]

def test_crawl_endpoint_monkeypatched(monkeypatch):
    async def fake_crawl_all(*args, **kwargs):
        return {"new_documents": 1, "new_alerts": 1}
    monkeypatch.setattr('app.api.routes.regintel.crawl_all', fake_crawl_all)
    resp = client.post("/api/v1/regintelligence/crawl")
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_documents"] == 1
    assert data["new_alerts"] == 1

def test_add_impact_monkeypatched(monkeypatch):
    # First, add an alert manually
    alert = {
        "alert_id": "test123",
        "source_key": "TEST_SRC",
        "authority": "Test Authority",
        "country": "Testland",
        "title": "Test Alert",
        "url": "http://example.com/alert",
        "doc_type": "regulation",
        "detected_at": "2024-01-01T00:00:00",
    }
    db_repo.feature_put("global", "regintel_alert", alert["alert_id"], alert)
    def fake_generate_text(prompt, max_tokens=None):
        return "Impact summary generated"
    monkeypatch.setattr('app.services.regintel_ai.generate_text', fake_generate_text)
    resp = client.post("/api/v1/regintelligence/alerts/test123/impact", json="some product")
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_summary"] == "Impact summary generated"


def test_crawl_all_filters_requested_source(monkeypatch):
    import asyncio
    from app.models.regintel_schemas import SourceKey
    from app.services import regintel_crawlers

    sources = [
        SourceKey(key="ONE", country="One", authority="One", listing_urls=["https://one.example"]),
        SourceKey(key="TWO", country="Two", authority="Two", listing_urls=["https://two.example"]),
    ]
    touched = []

    async def fake_crawl_source(source):
        if source.key != "ONE":
            raise AssertionError("should not crawl an unselected source")
        return []

    monkeypatch.setattr(regintel_crawlers, "get_sources", lambda: sources)
    monkeypatch.setattr(regintel_crawlers, "_crawl_source", fake_crawl_source)
    monkeypatch.setattr(__import__("app.services.regintel_store", fromlist=["touch_source"]), "touch_source", lambda key: touched.append(key))

    result = asyncio.run(regintel_crawlers.crawl_all(source_key="ONE"))
    assert result == {"new_documents": 0, "new_alerts": 0}
    assert touched == ["ONE"]
