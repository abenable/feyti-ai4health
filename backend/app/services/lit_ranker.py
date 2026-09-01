"""Literature relevance ranker – deterministic heuristic first, optional LLM.

The public ``rank_results`` function mirrors the behaviour of the original
implementation in ``regulate-api-core/lls/services/search_intelligence.py``.
It accepts a user query, a list of result dictionaries (as produced by the
scrapers), and optional region / topics filters. For up to 30 results the LLM
ranker is attempted; otherwise or on failure the deterministic heuristic is used.
"""

from __future__ import annotations
import json

import re
from datetime import date
from typing import List, Dict, Optional

from app.services.llm import generate_json

# ---------------------------------------------------------------------------
# LLM ranker – expects a JSON array of slim result objects.
# ---------------------------------------------------------------------------

_RANKER_PROMPT = """\
You are a biomedical literature relevance scorer. Score each publication for relevance to the search intent.

SEARCH INTENT:
- Original query: "{query}"
- Region filter: {region}
- Topics: {topics}

PUBLICATIONS (JSON array):
{publications_json}

For each publication, assign a relevance score 0-100:
- 90-100: Directly matches all criteria (topic + region + recency if specified)
- 70-89: Matches topic well, partial region/date match
- 50-69: Partially relevant
- 0-49: Weakly relevant or off-topic

Return ONLY a valid JSON array of objects:
[{"index": 0, "score": 85, "reason": "one sentence"}, ...]
"""

async def _llm_ranker(query: str, results: List[Dict], region: Optional[str], topics: List[str]) -> Dict[int, int]:
    slim = [
        {"index": i, "title": r.get("title", "")[:200], "abstract": (r.get("abstract") or "")[:300]}
        for i, r in enumerate(results)
    ]
    prompt = _RANKER_PROMPT.format(
        query=query,
        region=region or "any",
        topics=", ".join(topics) if topics else "general",
        publications_json=json.dumps(slim, ensure_ascii=False),
    )
    raw = await generate_json(prompt)
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
    scores = json.loads(raw)
    return {int(s["index"]): int(s.get("score", 50)) for s in scores}

# ---------------------------------------------------------------------------
# Deterministic heuristic ranker (copied from the original source).
# ---------------------------------------------------------------------------

def _heuristic_ranker(query: str, results: List[Dict], region: Optional[str], topics: List[str]) -> Dict[int, int]:
    current_year = date.today().year
    query_tokens = set(re.findall(r'\w+', query.lower()))
    score_map: Dict[int, int] = {}
    for i, r in enumerate(results):
        text = ((r.get('title') or '') + ' ' + (r.get('abstract') or '')).lower()
        title_text = (r.get('title') or '').lower()
        # Base token overlap
        text_tokens = set(re.findall(r'\w+', text))
        overlap = len(query_tokens & text_tokens)
        title_overlap = len(query_tokens & set(re.findall(r'\w+', title_text)))
        score = min(overlap * 4 + title_overlap * 8, 60)
        # Region bonus
        if region and region.lower() in text:
            score += 20
        # Topic keyword bonus
        topic_hits = sum(1 for t in topics if t in text)
        score += min(topic_hits * 5, 15)
        # Recency bonus (up to 5 points for last 3 years)
        pub_date = str(r.get('pub_date') or '')
        year_m = re.search(r'(20\d{2}|19\d{2})', pub_date)
        if year_m:
            yr = int(year_m.group(1))
            if yr >= current_year - 3:
                score += 5
        score_map[i] = min(score, 100)
    return score_map

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def rank_results(
    query: str,
    results: List[Dict],
    region: Optional[str] = None,
    topics: Optional[List[str]] = None,
) -> List[Dict]:
    """Add ``relevance_score`` and ``rank`` to each result, sorted descending.

    The function prefers the LLM ranker when the result set is small (≤30) but
    gracefully falls back to the deterministic heuristic on any error.
    """
    if not results:
        return results
    topics = topics or []
    score_map: Dict[int, int] = {}
    ai_ranked = False
    if len(results) <= 30:
        try:
            score_map = await _llm_ranker(query, results, region, topics)
            ai_ranked = True
        except Exception as exc:
            # LLM failed – fall back to heuristic.
            print(f"[SearchIntelligence] LLM ranker failed, using heuristic: {exc}")
    if not score_map:
        score_map = _heuristic_ranker(query, results, region, topics)
    scored = []
    for i, r in enumerate(results):
        item = dict(r)
        item['relevance_score'] = score_map.get(i, 50)
        item['ai_ranked'] = ai_ranked
        scored.append(item)
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    for rank, item in enumerate(scored, 1):
        item['rank'] = rank
    return scored
