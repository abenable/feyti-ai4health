import asyncio
import json
import pytest
from unittest.mock import AsyncMock

from app.services.regintel_store import (
    _SOURCES_PATH,
    _save,
    get_documents,
    get_alerts,
)
from app.services.regintel_crawlers import _content_hash, crawl_all

# Helper mock response
class MockResponse:
    def __init__(self, content: bytes):
        self.content = content
    def raise_for_status(self):
        pass

@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    # Ensure fresh sources and empty documents/alerts
    if _SOURCES_PATH.is_file():
        _SOURCES_PATH.unlink()
    # write a single source with test listing URL
    source = [{
        "key": "TEST_SRC",
        "country": "Testland",
        "authority": "Test Authority",
        "listing_urls": ["http://example.com/list"],
        "enabled": True,
    }]
    _save(_SOURCES_PATH, source)
    # Ensure documents and alerts are empty
    from app.services.regintel_store import _DOCUMENTS_PATH, _ALERTS_PATH
    if _DOCUMENTS_PATH.is_file():
        _DOCUMENTS_PATH.unlink()
    if _ALERTS_PATH.is_file():
        _ALERTS_PATH.unlink()
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
