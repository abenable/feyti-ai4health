"""Literature query builder – LLM first with deterministic fallback.

Provides ``build_search_params`` which returns a dict describing the structured
search parameters derived from a free‑text query. The implementation mirrors the
logic from ``regulate-api-core/lls/services/search_intelligence.py`` but uses the
asynchronous LLM helper ``app.services.llm.generate_json``.
"""

from __future__ import annotations

import re
import json
from datetime import date
from typing import Dict, List, Optional

from app.services.llm import generate_json

# ---------------------------------------------------------------------------
# Static data – country list and topic keywords (copied from the original
# implementation). Keeping them local avoids a heavy import chain.
# ---------------------------------------------------------------------------

_COUNTRIES = [
    'Afghanistan','Albania','Algeria','Angola','Argentina','Armenia','Australia',
    'Austria','Azerbaijan','Bahamas','Bahrain','Bangladesh','Belarus','Belgium',
    'Belize','Benin','Bolivia','Botswana','Brazil','Bulgaria','Burkina Faso',
    'Burundi','Cambodia','Cameroon','Canada','Chad','Chile','China','Colombia',
    'Congo','Costa Rica','Croatia','Cuba','Cyprus','Denmark','Djibouti',
    'Dominican Republic','Ecuador','Egypt','El Salvador','Eritrea','Estonia',
    'Eswatini','Ethiopia','Fiji','Finland','France','Gabon','Gambia','Georgia',
    'Germany','Ghana','Greece','Guatemala','Guinea','Guyana','Haiti','Honduras',
    'Hungary','Iceland','India','Indonesia','Iran','Iraq','Ireland','Israel',
    'Italy','Jamaica','Japan','Jordan','Kazakhstan','Kenya','Kuwait',
    'Kyrgyzstan','Laos','Latvia','Lebanon','Lesotho','Liberia','Libya',
    'Lithuania','Luxembourg','Madagascar','Malawi','Malaysia','Mali','Malta',
    'Mauritania','Mauritius','Mexico','Moldova','Mongolia','Montenegro',
    'Morocco','Mozambique','Myanmar','Namibia','Nepal','Netherlands',
    'New Zealand','Nicaragua','Niger','Nigeria','Norway','Oman','Pakistan',
    'Palestine','Panama','Paraguay','Peru','Philippines','Poland','Portugal',
    'Qatar','Romania','Russia','Rwanda','Saudi Arabia','Senegal','Serbia',
    'Sierra Leone','Singapore','Slovakia','Slovenia','Somalia','South Africa',
    'South Korea','South Sudan','Spain','Sri Lanka','Sudan','Suriname',
    'Sweden','Switzerland','Syria','Taiwan','Tajikistan','Tanzania','Thailand',
    'Togo','Trinidad and Tobago','Tunisia','Turkey','Turkmenistan','Uganda',
    'Ukraine','United Arab Emirates','United Kingdom','United States',
    'Uruguay','Uzbekistan','Venezuela','Vietnam','Yemen','Zambia','Zimbabwe',
    # Common variants
    'USA','UK','UAE','DRC','CAR','East Africa','West Africa','Sub-Saharan Africa',
    'Africa','Europe','Asia','Latin America','Caribbean','Middle East',
]

_COUNTRIES_LOWER = {c.lower(): c for c in _COUNTRIES}

_TOPIC_KEYWORDS = [
    'adverse', 'safety', 'toxicity', 'pharmacovigilance', 'drug reaction',
    'side effect', 'case report', 'prevalence', 'incidence', 'mortality',
    'clinical trial', 'randomized', 'systematic review', 'meta-analysis',
    'treatment', 'therapy', 'efficacy', 'resistance', 'outbreak', 'epidemic',
]

# ---------------------------------------------------------------------------
# Prompt template – identical to the original source (trimmed for brevity).
# ---------------------------------------------------------------------------

_QUERY_BUILDER_PROMPT = """\
You are a biomedical search query analyst. Analyze the user's search query and extract structured information.

USER QUERY: "{query}"

Extract and return ONLY a valid JSON object (no markdown, no explanation):
{{
  "rewritten_query": "<cleaned search terms without region/date, optimized for PubMed/Semantic Scholar>",
  "mesh_query": "<PubMed MeSH-style query e.g. (HIV[MeSH] OR HIV Infections[MeSH]) AND Uganda[MeSH]>",
  "detected_region": "<country or region name, or null>",
  "detected_year_from": <4-digit year or null>,
  "detected_year_to": <4-digit year or null>,
  "detected_topics": ["<topic1>", "<topic2>"],
  "suggested_filters": {{
    "region": "<detected region or null>",
    "year_from": <year or null>,
    "year_to": <year or null>
  }},
  "reasoning": "<one sentence explaining what was extracted>"
}}

Rules:
- rewritten_query: remove country/year from the query, keep medical terms
- mesh_query: use proper MeSH headings where possible
- detected_region: extract country/region if mentioned (e.g. "Uganda", "East Africa")
- detected_year_from/to: extract if mentioned (e.g. "2015-2024", "last 5 years" → compute from current year {current_year})
- If no region/year found, use null
"""

# ---------------------------------------------------------------------------
# LLM‑based builder
# ---------------------------------------------------------------------------

async def _llm_query_builder(query: str) -> Dict:
    current_year = date.today().year
    prompt = _QUERY_BUILDER_PROMPT.format(query=query, current_year=current_year)
    raw = await generate_json(prompt)
    # Strip possible markdown fences – the LLM helper already does this but be safe.
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

# ---------------------------------------------------------------------------
# Rule‑based fallback (deterministic)
# ---------------------------------------------------------------------------

def _rule_based_query_builder(query: str) -> Dict:
    current_year = date.today().year
    q = query.strip()

    # Detect region
    detected_region = None
    for word in re.findall(r'[A-Za-z][A-Za-z\s\-]{1,30}', q):
        if word.strip().lower() in _COUNTRIES_LOWER:
            detected_region = _COUNTRIES_LOWER[word.strip().lower()]
            break

    # Detect years
    year_from = year_to = None
    range_m = re.search(r'\b(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|19\d{2})\b', q)
    if range_m:
        year_from, year_to = int(range_m.group(1)), int(range_m.group(2))
    else:
        last_m = re.search(r'last\s+(\d+)\s+years?', q, re.I)
        if last_m:
            year_from = current_year - int(last_m.group(1))
            year_to = current_year
        else:
            single_m = re.search(r'\b(20\d{2}|19\d{2})\b', q)
            if single_m:
                year_from = year_to = int(single_m.group(1))

    # Clean query (remove region and year tokens)
    clean = q
    if detected_region:
        clean = re.sub(re.escape(detected_region), '', clean, flags=re.I)
    clean = re.sub(r'\b(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|19\d{2})\b', '', clean)
    clean = re.sub(r'\b(20\d{2}|19\d{2})\b', '', clean)
    clean = re.sub(r'last\s+\d+\s+years?', '', clean, flags=re.I)
    clean = re.sub(r'\s{2,}', ' ', clean).strip().strip(',').strip()

    topics = [kw for kw in _TOPIC_KEYWORDS if kw in q.lower()]

    return {
        'rewritten_query': clean or q,
        'mesh_query': clean or q,
        'detected_region': detected_region,
        'detected_year_from': year_from,
        'detected_year_to': year_to,
        'detected_topics': topics,
        'suggested_filters': {
            'region': detected_region,
            'year_from': year_from,
            'year_to': year_to,
        },
        'reasoning': 'Extracted using rule‑based NLP (no LLM key available).',
    }

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def build_search_params(query: str) -> Dict:
    """Return structured search parameters for *query*.

    Tries the LLM builder first; on any error falls back to the deterministic
    rule‑based implementation. The returned dict always contains the keys from
    the original specification and additionally ``ai_enhanced`` (bool) and
    ``original_query`` (the raw user input).
    """
    try:
        result = await _llm_query_builder(query)
        result['ai_enhanced'] = True
    except Exception as exc:
        # LLM unavailable or malformed response – use deterministic fallback.
        result = _rule_based_query_builder(query)
        result['ai_enhanced'] = False
    result['original_query'] = query
    return result
