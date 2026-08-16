"""Draft output validation for a CTD section, before a reviewer can approve it.

Same split as readiness_service: deterministic checks produce the score and
the gate, the LLM only narrates unsupported claims. The Approve button reads
`score`/`checks` from here and refuses to fire while any `error`-level check
is open — today's `/dossier/approve` accepts anything, this is the gate that
was missing.
"""

from __future__ import annotations

import logging
import re

from app.services import llm
from app.services.ctd_map import CTD_MAP
from app.services.generation_service import GAP_MARKER

logger = logging.getLogger(__name__)

_MIN_WORDS = 40  # floor below which a "complete" draft is almost certainly a stub


def _immediate_children(ctd_path: str) -> list[tuple[str, str]]:
    """Direct child sections one level below ctd_path, per the flat CTD_MAP."""
    depth = ctd_path.count(".") + 1
    prefix = f"{ctd_path}."
    return sorted(
        (p, t) for p, t in CTD_MAP.items()
        if p.startswith(prefix) and p.count(".") == depth
    )


def _check_h1(markdown: str, title: str) -> dict | None:
    first_line = next((ln.strip() for ln in markdown.splitlines() if ln.strip()), "")
    if not first_line.startswith("# "):
        return {"id": "h1_present", "level": "error",
                "message": "Document does not open with a single H1 heading.", "line": 1}
    if title and title.lower() not in first_line.lower():
        return {"id": "h1_present", "level": "warn",
                "message": f"H1 does not mention the section title ({title!r}).", "line": 1}
    return None


def _check_path(markdown: str, section_path: str) -> dict | None:
    if section_path and section_path not in markdown[:500]:
        return {"id": "path_present", "level": "warn",
                "message": f"CTD path {section_path} does not appear in the opening paragraph.",
                "line": 1}
    return None


def _check_subsections(markdown: str, section_path: str) -> list[dict]:
    children = _immediate_children(section_path)
    if not children:
        return []
    headings = "\n".join(ln for ln in markdown.splitlines() if ln.strip().startswith("#")).lower()
    missing = [f"{p} {t}" for p, t in children if t.lower() not in headings]
    if not missing:
        return []
    return [{"id": "missing_subsections", "level": "warn",
             "message": f"{len(missing)} expected subsection(s) not found as headings: "
                        + "; ".join(missing[:5]) + (" …" if len(missing) > 5 else ""),
             "line": None}]


def _check_gaps(markdown: str) -> list[dict]:
    checks = []
    for i, line in enumerate(markdown.splitlines(), start=1):
        if GAP_MARKER in line:
            checks.append({"id": "open_gaps", "level": "error",
                            "message": line.strip().lstrip("> ").strip(), "line": i})
    return checks


def _check_unused_fields(markdown: str, fields: list[dict]) -> list[dict]:
    unused = [f["label"] for f in fields
              if f.get("value") and f["value"] not in markdown]
    if not unused:
        return []
    return [{"id": "unused_fields", "level": "warn",
             "message": f"{len(unused)} extracted field(s) not reflected in the draft: "
                        + ", ".join(unused[:5]) + (" …" if len(unused) > 5 else ""),
             "line": None}]


def _check_length(markdown: str) -> dict | None:
    words = len(markdown.split())
    if words < _MIN_WORDS:
        return {"id": "too_short", "level": "warn",
                "message": f"Draft is only {words} words — likely incomplete.", "line": None}
    return None


def run_checks(markdown: str, meta: dict) -> list[dict]:
    """Deterministic checks only — no LLM call."""
    checks: list[dict] = []
    title = meta.get("title", "")
    section_path = meta.get("section_path", "")
    fields = meta.get("fields") or []

    if not markdown.strip():
        return [{"id": "empty_draft", "level": "error",
                 "message": "No draft has been generated yet.", "line": None}]

    for c in (_check_h1(markdown, title), _check_path(markdown, section_path), _check_length(markdown)):
        if c:
            checks.append(c)
    checks.extend(_check_subsections(markdown, section_path))
    checks.extend(_check_gaps(markdown))
    checks.extend(_check_unused_fields(markdown, fields))
    return checks


def _score(checks: list[dict]) -> int:
    errors = sum(1 for c in checks if c["level"] == "error")
    warnings = sum(1 for c in checks if c["level"] == "warn")
    return max(0, 100 - errors * 20 - warnings * 5)


def _build_narrative_prompt(markdown: str, extracted_text: str, meta: dict) -> str:
    return (
        "You are a regulatory reviewer checking a drafted CTD section for claims "
        "that are not supported by its source document.\n\n"
        f"SECTION: {meta.get('section_path', '')} {meta.get('title', '')}\n\n"
        "SOURCE TEXT (ground truth — nothing outside this may be presented as fact):\n"
        "---\n" + extracted_text[:6000] + "\n---\n\n"
        "DRAFT TO CHECK:\n---\n" + markdown[:6000] + "\n---\n\n"
        "List, as short markdown bullets, any sentence in the draft that states a "
        "specific fact (number, date, result, name) NOT present in the source text. "
        "Ignore standard regulatory boilerplate and section structure — only flag "
        "invented facts. If nothing is unsupported, respond with exactly: "
        "'No unsupported claims found.'"
    )


async def validate_document(markdown: str, extracted_text: str, meta: dict) -> dict:
    checks = run_checks(markdown, meta)
    open_gaps = sum(1 for c in checks if c["id"] == "open_gaps")
    score = _score(checks)

    if not markdown.strip():
        narrative = "_Nothing to validate — no draft has been generated yet._"
    else:
        try:
            narrative = await llm.generate_text(_build_narrative_prompt(markdown, extracted_text, meta))
        except Exception:
            logger.warning("validation narrative generation failed", exc_info=True)
            narrative = ("_AI narrative unavailable — the analysis service could not "
                         "be reached. The checks above are still accurate._")

    return {"checks": checks, "open_gaps": open_gaps, "score": score, "narrative": narrative}


if __name__ == "__main__":  # self-check: python -m app.services.validation_service
    meta = {"section_path": "3.2.P.8.3", "title": "Stability Data",
            "fields": [{"label": "batch numbers", "value": "AB123"}]}

    bad = "Some text without a heading.\n" + f"> {GAP_MARKER}: 24-month assay results\n"
    checks = run_checks(bad, meta)
    ids = {c["id"] for c in checks}
    assert "h1_present" in ids and "open_gaps" in ids and "unused_fields" in ids and "too_short" in ids
    assert _score(checks) < 100

    good = (
        "# Stability Data (3.2.P.8.3)\n\n"
        "Batch AB123 was tested under ICH conditions for stability.\n" * 10
    )
    good_checks = run_checks(good, {"section_path": "3.2.P.8.3", "title": "Stability Data",
                                     "fields": [{"label": "batch numbers", "value": "AB123"}]})
    assert not any(c["level"] == "error" for c in good_checks), good_checks
    assert _score(good_checks) == 100

    assert run_checks("", meta)[0]["id"] == "empty_draft"
    print("OK — validation_service deterministic checks + scoring")
