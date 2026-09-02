import asyncio
import json
import pytest
from unittest.mock import AsyncMock

from app.services import db_repo
from app.services.regintel_store import get_documents, get_alerts
from app.services.regintel_crawlers import _content_hash, crawl_all

# Helper mock response
class MockResponse:
    def __init__(self, content: bytes):
        self.content = content
    def raise_for_status(self):
        pass

@pytest.fixture(autouse=True)
def clean_store():
    # Fresh DB per test (conftest); install a single test source.
    db_repo.feature_put("global", "regintel_source", "TEST_SRC", {
        "key": "TEST_SRC",
        "country": "Testland",
        "authority": "Test Authority",
        "listing_urls": ["http://example.com/list"],
        "enabled": True,
    })
    yield

def test_crawl_extraction_and_storage(monkeypatch):
    # HTML fixture with two PDF links, one non-doc, one mailto
    listing_html = """
    <html><body>
        <a href=\"doc1.pdf\">Regulation One</a>
        <a href=\"doc2.pdf\">Guideline Two</a>
        <a href=\"page.html\">Home Page</a>
        <a href=\"mailto:test@example.com\">Email</a>
    </body></html>
    """
    async def mock_get(self, url, timeout=None):
        if url == "http://example.com/list":
            return MockResponse(listing_html.encode())
        elif url.endswith('.pdf'):
            return MockResponse(b"PDF content bytes")
        else:
            return MockResponse(b"")
    monkeypatch.setattr('httpx.AsyncClient.get', mock_get)
    import asyncio
    result = asyncio.run(crawl_all())
    assert result["new_documents"] == 2
    assert result["new_alerts"] == 2
    docs = get_documents()
    alerts = get_alerts()
    assert len(docs) == 2
    assert len(alerts) == 2
    titles = {d["title"] for d in docs}
    assert titles == {"Regulation One", "Guideline Two"}

def test_content_hash_stability():
    txt = "Sample text for hashing"
    h1 = _content_hash(txt)
    h2 = _content_hash(txt)
    assert h1 == h2
    h3 = _content_hash(txt + " extra")
    assert h1 != h3
