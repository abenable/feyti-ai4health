"""Literature scrapers – async httpx versions of the original sync implementations.

Each function returns a list of dictionaries with a normalized shape:
    {
        "title": str,
        "url": str,
        "abstract": str,
        "source": str,  # e.g. "pubmed", "semantic_scholar", etc.
        "year": str,    # extracted year as string (may be empty)
        "doi": str,
    }

The public API runs all scrapers in parallel with a per‑source timeout. A failing
source returns an empty list and never aborts the overall search.
"""

from __future__ import annotations

import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import httpx


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": "FeytiLitBot/1.0 (mailto:nkansiime@feytimedicalgroup.com)"
}

async def _get_json(url: str, params: dict | None = None) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

async def _get_text(url: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text

def _extract_year(date_str: str) -> str:
    m = re.search(r"(20\d{2}|19\d{2})", date_str or "")
    return m.group(1) if m else ""

# ---------------------------------------------------------------------------
# PubMed (NCBI E‑utilities)
# ---------------------------------------------------------------------------

async def search_pubmed(
    query: str,
    max_results: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    search_query = query
    if region and region.lower() not in query.lower():
        search_query = f"{query} AND {region}[Affiliation]"

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params: Dict = {
        "db": "pubmed",
        "term": search_query,
        "retmax": max_results,
        "retmode": "json",
        "usehistory": "y",
    }
    if date_from or date_to:
        params["datetype"] = "pdat"
        if date_from:
            params["mindate"] = date_from.replace("-", "/")
        if date_to:
            params["maxdate"] = date_to.replace("-", "/")
    try:
        data = await _get_json(base_url, params)
    except Exception as exc:
        print(f"[PubMed] Search request failed: {exc}")
        return []

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # Fetch summary
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
    try:
        summary = await _get_json(fetch_url, fetch_params)
    except Exception as exc:
        print(f"[PubMed] Fetch details failed: {exc}")
        return []

    # Fetch DOI via eFetch XML (simplified – we only try to get DOI if possible)
    doi_map: Dict[str, str] = {}
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    efetch_params = {"db": "pubmed", "id": ",".join(ids), "rettype": "xml", "retmode": "xml"}
    try:
        xml_text = await _get_text(efetch_url)
        blocks = re.split(r"<PubmedArticle>", xml_text or "")
        for block in blocks[1:]:
            pmid_m = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
            doi_m = re.search(r"<ArticleId IdType=\"doi\">([^<]+)</ArticleId>", block)
            if pmid_m and doi_m:
                doi_map[pmid_m.group(1)] = doi_m.group(1).strip()
    except Exception:
        pass

    results: List[Dict] = []
    for uid in ids:
        article = summary.get("result", {}).get(uid, {})
        doi = doi_map.get(uid, "")
        results.append(
            {
                "title": article.get("title", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                "abstract": article.get("abstract", ""),
                "source": "pubmed",
                "year": _extract_year(article.get("pubdate", "")),
                "doi": doi,
            }
        )
    return results

# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

async def search_semantic_scholar(
    query: str,
    max_results: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    search_query = query
    if region and region.lower() not in query.lower():
        search_query = f"{query} {region}"

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params: Dict = {
        "query": search_query,
        "limit": min(max_results, 100),
        "fields": "title,authors,year,abstract,externalIds,paperId,publicationDate,openAccessPdf",
    }
    if date_from:
        try:
            params["year"] = f"{int(date_from[:4])}-"
        except Exception:
            pass
    if date_to:
        try:
            params["year"] = f"-{int(date_to[:4])}"
        except Exception:
            pass
    req_headers = dict(HEADERS)
    s2_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if s2_key:
        req_headers["x-api-key"] = s2_key
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=req_headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        print(f"[Semantic Scholar] Search failed: {exc}")
        return []

    results: List[Dict] = []
    for item in data.get("data", []):
        ext = item.get("externalIds") or {}
        doi = ext.get("DOI", "")
        pmid = ext.get("PubMed", "")
        paper_id = item.get("paperId", "")
        open_pdf = (item.get("openAccessPdf") or {}).get("url", "")
        if paper_id:
            paper_url = f"https://www.semanticscholar.org/paper/{paper_id}"
        elif doi:
            paper_url = f"https://doi.org/{doi}"
        elif pmid:
            paper_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        else:
            paper_url = open_pdf
        pub_date = item.get("publicationDate") or str(item.get("year", ""))
        if date_from and pub_date[:10] < date_from:
            continue
        if date_to and pub_date[:10] > date_to:
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "url": paper_url,
                "abstract": item.get("abstract") or "",
                "source": "semantic_scholar",
                "year": _extract_year(pub_date),
                "doi": doi,
            }
        )
    return results

# ---------------------------------------------------------------------------
# PLOS ONE
# ---------------------------------------------------------------------------

async def search_plos_one(
    query: str,
    max_results: int = 30,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    search_q = f'everything:"{query}"'
    if region and region.lower() not in query.lower():
        search_q = f'everything:"{query} {region}"'

    date_filter = None
    if date_from or date_to:
        solr_from = f"{date_from}T00:00:00Z" if date_from else "*"
        solr_to = f"{date_to}T23:59:59Z" if date_to else "*"
        date_filter = f"publication_date:[{solr_from} TO {solr_to}]"

    params: Dict = {
        "q": search_q,
        "fq": f"journal_key:PLoSONE{(' AND ' + date_filter) if date_filter else ''}",
        "fl": "id,title_display,author_display,abstract,publication_date",
        "rows": min(max_results, 50),
        "wt": "json",
        "start": 0,
    }
    try:
        data = await _get_json("https://api.plos.org/search", params)
    except Exception as exc:
        print(f"[PLOS ONE] Search failed: {exc}")
        return []

    results: List[Dict] = []
    for item in data.get("response", {}).get("docs", []):
        doi = item.get("id", "")
        paper_url = f"https://journals.plos.org/plosone/article?id={doi}" if doi else ""
        title_raw = item.get("title_display", "")
        title = title_raw.replace("<em>", "").replace("</em>", "") if title_raw else ""
        pub_date = (item.get("publication_date") or "")[:10]
        abstract_raw = item.get("abstract", "")
        abstract = abstract_raw[0] if isinstance(abstract_raw, list) else (abstract_raw or "")
        results.append(
            {
                "title": title,
                "url": paper_url,
                "abstract": abstract,
                "source": "plos_one",
                "year": _extract_year(pub_date),
                "doi": doi,
            }
        )
    return results

# ---------------------------------------------------------------------------
# Springer (requires API key)
# ---------------------------------------------------------------------------

async def _search_springer_base(
    query: str,
    max_results: int,
    date_from: Optional[str],
    date_to: Optional[str],
    region: Optional[str],
    source_name: str,
) -> List[Dict]:
    api_key = os.getenv("SPRINGER_API_KEY")
    if not api_key:
        print(f"[{source_name}] SPRINGER_API_KEY not set, skipping")
        return []
    q_parts = [f'title:"{query}" OR keyword:"{query}"']
    if region and region.lower() not in query.lower():
        q_parts.append(f'keyword:"{region}"')
    if date_from:
        q_parts.append(f'date>={date_from}')
    if date_to:
        q_parts.append(f'date<={date_to}')
    params: Dict = {
        "q": " AND ".join(q_parts),
        "p": min(max_results, 50),
        "s": 1,
        "api_key": api_key,
    }
    try:
        data = await _get_json("https://api.springer.com/meta/v2/json", params)
    except Exception as exc:
        print(f"[{source_name}] Search failed: {exc}")
        return []
    results: List[Dict] = []
    for item in data.get("records", []):
        doi = item.get("doi", "")
        url_field = item.get("url", [{}])
        if isinstance(url_field, list):
            paper_url = next((u.get("value", "") for u in url_field if u.get("format") == "html"), doi and f"https://doi.org/{doi}" or "")
        else:
            paper_url = f"https://doi.org/{doi}" if doi else ""
        creators = item.get("creators", [])
        authors = ", ".join(c.get("creator", "") for c in creators if c.get("creator"))
        pub_date = item.get("publicationDate", "") or item.get("onlineDate", "")
        results.append(
            {
                "title": item.get("title", ""),
                "url": paper_url,
                "abstract": item.get("abstract", ""),
                "source": source_name.lower(),
                "year": _extract_year(pub_date),
                "doi": doi,
            }
        )
    return results

async def search_springer(
    query: str,
    max_results: int = 25,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    return await _search_springer_base(query, max_results, date_from, date_to, region, "springer")

async def search_bmc(
    query: str,
    max_results: int = 25,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    return await _search_springer_base(query, max_results, date_from, date_to, region, "bmc")

# ---------------------------------------------------------------------------
# Local sources – PAMJ and Uganda Ministry of Health (light stubs)
# ---------------------------------------------------------------------------

async def search_pamj(
    query: str,
    max_results: int = 30,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    # Placeholder implementation – returns empty list. Real implementation would
    # fetch the PAMJ recent‑articles page and parse it with BeautifulSoup.
    return []

async def search_health_go_ug(
    query: str,
    max_results: int = 30,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict]:
    # Placeholder – returns empty list. The real scraper parses static HTML.
    return []

# ---------------------------------------------------------------------------
# Public helper to run all sources in parallel with per‑source timeout.
# ---------------------------------------------------------------------------

async def run_all_scrapers(
    query: str,
    max_results: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
    timeout: float = 10.0,
) -> List[Dict]:
    """Execute all scraper coroutines concurrently.

    Each scraper is wrapped with ``asyncio.wait_for`` so that a slow or failing
    source does not block the overall search. Exceptions are caught and result in
    an empty list for that source.
    """
    scrapers = [
        search_pubmed(query, max_results, date_from, date_to, region),
        search_semantic_scholar(query, max_results, date_from, date_to, region),
        search_plos_one(query, max_results, date_from, date_to, region),
        search_springer(query, max_results, date_from, date_to, region),
        search_bmc(query, max_results, date_from, date_to, region),
        search_pamj(query, max_results, date_from, date_to, region),
        search_health_go_ug(query, max_results, date_from, date_to, region),
    ]
    results: List[Dict] = []
    for coro in asyncio.as_completed([asyncio.wait_for(c, timeout) for c in scrapers]):
        try:
            src_res = await coro
            if src_res:
                results.extend(src_res)
        except Exception:
            continue
    return results
