import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx
try:
    from bs4 import BeautifulSoup
except ImportError:
    # Fallback minimal HTML parser using stdlib
    from html.parser import HTMLParser
    import re
    class _SimpleSoup:
        def __init__(self, html: str):
            self.html = html
        def find_all(self, tag: str, href: bool = False):
            if tag != "a" or not href:
                return []
            pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
            matches = []
            for m in pattern.finditer(self.html):
                href_val = m.group(1)
                inner = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                # mimic bs4 Tag with dict-like access
                class _Tag(dict):
                    def __init__(self, href, text):
                        super().__init__(href=href)
                        self._text = text
                    def get(self, key, default=None):
                        return self[key] if key in self else default
                    def __getitem__(self, key):
                        return super().get(key)
                    def get_text(self, strip=False):
                        return self._text.strip() if strip else self._text
                matches.append(_Tag(href=href_val, text=inner))
            return matches
    BeautifulSoup = _SimpleSoup
from urllib.parse import urljoin

from app.models.regintel_schemas import RegulatoryAlert, SourceKey
from app.services.regintel_store import (
    add_or_update_document,
    get_sources,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

DOC_KEYWORDS = [
    "guideline", "regulation", "notice", "circular", "policy", "directive",
    "approval", "registration", "recall", "alert", "safety", "bulletin",
    "gazette", "act", "standard", "procedure", "requirement", "framework",
    "notification", "order", "decree", "instruction", "communiqué",
]

PDF_EXTENSIONS = (".pdf", ".PDF")

_GENERIC_LINK_TEXTS = {
    "download", "click here", "here", "pdf", "view", "open", "read more",
    "read", "more", "link", "file", "document", "doc", "attachment", "get",
}


def _is_doc_link(href: str, text: str) -> bool:
    text_lower = text.lower()
    return any(k in text_lower for k in DOC_KEYWORDS) or href.lower().endswith(PDF_EXTENSIONS)


def _content_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def _extract_title_from_context(a_tag, href: str) -> str:
    # 1. explicit attributes
    for attr in ("aria-label", "title"):
        val = (a_tag.get(attr) or "").strip()
        if val and val.lower() not in _GENERIC_LINK_TEXTS:
            return val

    link_text = a_tag.get_text(strip=True)

    # 2. container heuristics
    for parent in a_tag.parents:
        tag_name = getattr(parent, "name", None)
        if tag_name in ("li", "td", "div", "article", "section", "p"):
            for sib in parent.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b"]):
                sib_text = sib.get_text(strip=True)
                if sib_text and sib_text.lower() not in _GENERIC_LINK_TEXTS and sib_text != link_text:
                    return sib_text[:300]
            container_text = parent.get_text(separator=" ", strip=True).replace(link_text, "").strip(" |–-·")
            if len(container_text) > 10 and container_text.lower() not in _GENERIC_LINK_TEXTS:
                return container_text[:300]
            break

    # 3. filename fallback
    from urllib.parse import urlparse, unquote

    path = urlparse(href).path
    filename = path.rstrip("/").split("/")[-1]
    filename = unquote(filename)
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    name = name.replace("-", " ").replace("_", " ").strip()
    if name and name.lower() not in _GENERIC_LINK_TEXTS:
        return name.title()[:300]
    return ""


async def _fetch(client: httpx.AsyncClient, url: str, timeout: int = 20) -> Optional[bytes]:
    try:
        resp = await client.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


async def _process_link(client: httpx.AsyncClient, base_url: str, href: str, a_tag) -> Optional[RegulatoryAlert]:
    abs_url = urljoin(base_url, href)
    if not abs_url.startswith("http"):
        return None

    # Determine title
    text = a_tag.get_text(strip=True)
    title = text if text.lower() not in _GENERIC_LINK_TEXTS and len(text) >= 5 else _extract_title_from_context(a_tag, href)
    if not title:
        title = "Untitled Document"

    content_bytes = await _fetch(client, abs_url)
    if not content_bytes:
        return None
    # Simple text extraction: strip HTML tags
    if abs_url.lower().endswith(PDF_EXTENSIONS):
        # PDF handling omitted for test fixtures – treat as empty
        content = ""
    else:
        soup = BeautifulSoup(content_bytes, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)
    if len(content) < 100:
        # ignore tiny pages
        return None
    chash = _content_hash(content)
    # Record document
    doc_record = {
        "source_key": "",  # filled by caller
        "url": abs_url,
        "title": title,
        "content_hash": chash,
        "doc_type": "regulation",
        # timestamps added in store function
    }
    # Store will set timestamps
    add_or_update_document(doc_record)
    # Create alert placeholder – source info will be filled later
    return RegulatoryAlert(
        source_key="",
        authority="",
        country="",
        title=title,
        url=abs_url,
        doc_type="regulation",
    )


async def _crawl_source(source: SourceKey) -> List[RegulatoryAlert]:
    alerts: List[RegulatoryAlert] = []
    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
        for listing_url in source.listing_url.split("|") if isinstance(source.listing_url, str) else []:
            # Some placeholder seeds may store multiple URLs separated by '|'
            content = await _fetch(client, listing_url)
            if not content:
                continue
            soup = BeautifulSoup(content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = a.get_text(strip=True)
                if not href or not _is_doc_link(href, text):
                    continue
                alert = await _process_link(client, listing_url, href, a)
                if alert:
                    # Fill source metadata
                    alert.source_key = source.key
                    alert.authority = source.authority
                    alert.country = source.country
                    alerts.append(alert)
    return alerts


async def crawl_all(enabled_only: bool = True) -> dict:
    """Crawl all configured sources.
    Returns a dict with counts of new documents and alerts.
    """
    sources = get_sources()
    if enabled_only:
        sources = [s for s in sources if s.enabled]
    tasks = [_crawl_source(s) for s in sources]
    results = await asyncio.gather(*tasks)
    all_alerts: List[RegulatoryAlert] = []
    for alerts in results:
        all_alerts.extend(alerts)
    # Persist alerts
    for alert in all_alerts:
        from app.services.regintel_store import add_alert

        add_alert(alert)
    return {
        "new_documents": len(all_alerts),
        "new_alerts": len(all_alerts),
    }
