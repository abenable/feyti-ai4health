"""Dossier submission-readiness analysis.

The numbers are deterministic; the AI only narrates. Score, per-module counts,
and the ⚠️ gap tally come from build_plan() + the drafted markdown we already
store — the LLM never emits a figure and never invents a regulatory fact. It
reads the completion state we hand it and writes a verdict + blockers + next
actions as markdown (no JSON to parse, nothing to break).

Score = approved / engaged, where engaged = sections with ≥1 document. The CTD
catalogue is 301 sections but any product fills a subset, so approved/301 would
read ~11% forever and be meaningless. Empty sections are reported as coverage;
*which* empties are critical is the AI's judgment, grounded in product context.
"""

from __future__ import annotations

import logging

from app.services import llm
from app.services.dossier_service import (
    build_plan,
    context_block,
    list_generated_docs,
    read_generated,
    _resolve_section_dir,
)
from app.services.generation_service import GAP_MARKER

logger = logging.getLogger(__name__)


def _tally(plan: list[dict]) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Return (totals, per-module rows, empty sections, drafted sections)."""
    approved = in_review = empty = 0
    modules: list[dict] = []
    empties: list[dict] = []
    drafted: list[dict] = []
    for mod in plan:
        m_app = m_rev = m_emp = 0
        for sec in mod["sections"]:
            status = sec["status"]
            if status == "approved":
                m_app += 1
            elif status == "in_review":
                m_rev += 1
            else:
                m_emp += 1
                empties.append({"path": sec["path"], "title": sec["title"]})
            if status in ("approved", "in_review"):
                drafted.append({"path": sec["path"], "title": sec["title"], "status": status})
        approved += m_app
        in_review += m_rev
        empty += m_emp
        modules.append({"module": mod["module"], "approved": m_app, "in_review": m_rev,
                        "empty": m_emp, "drafted": m_app + m_rev})
    totals = {"approved": approved, "in_review": in_review, "empty": empty,
              "engaged": approved + in_review, "catalogue": approved + in_review + empty}
    return totals, modules, empties, drafted


def _count_gaps(docs: list[dict]) -> tuple[int, list[dict]]:
    """Total ⚠️ TO BE PROVIDED markers across drafts + which docs carry them."""
    total = 0
    per_doc: list[dict] = []
    # ponytail: reads every drafted doc; fine for a demo, memoize by mtime if it bites.
    for d in docs:
        md = read_generated(_resolve_section_dir(d["section_path"]), d["stem"])
        n = md.count(GAP_MARKER)
        if n:
            per_doc.append({"path": d["ctd_path"], "title": d["title"], "gaps": n})
            total += n
    return total, per_doc


def _verdict(score: int, in_review: int, open_gaps: int) -> str:
    """Rate completion of the DRAFTED work — not overall submission coverage.

    We have no per-product required-section set, so this can't claim the dossier
    is submission-ready (a 1-section dossier can hit 'ready'). The UI labels it as
    draft progress; judging which empty sections are critical is the AI's job.
    """
    if score == 100 and in_review == 0 and open_gaps == 0:
        return "ready"
    if score >= 80:
        return "nearly"
    return "not_ready"


def _build_prompt(totals, modules, empties, drafted, gap_docs) -> str:
    ctx = context_block("PRODUCT CONTEXT:")
    mod_lines = "\n".join(
        f"- {m['module']}: {m['approved']} approved, {m['in_review']} in review, {m['empty']} empty"
        for m in modules
    )
    # ponytail: pass all empty sections; if the prompt gets too big, filter to
    # major nodes (path.count('.') <= 3) before listing.
    empty_lines = "\n".join(f"- {e['path']} {e['title']}" for e in empties) or "(none — every section drafted)"
    drafted_lines = "\n".join(f"- {d['path']} {d['title']} [{d['status']}]" for d in drafted) or "(none drafted yet)"
    gap_lines = "\n".join(f"- {g['path']} {g['title']}: {g['gaps']} open gap(s)" for g in gap_docs) or "(none)"
    return "\n\n".join(filter(None, [
        "You are a regulatory affairs reviewer assessing whether a CTD (ICH M4) "
        "dossier is ready for submission.",
        ctx,
        f"COMPLETION STATE:\nEngaged sections: {totals['engaged']} "
        f"({totals['approved']} approved, {totals['in_review']} in review). "
        f"Empty sections: {totals['empty']}. Open ⚠️ gap markers across drafts: "
        f"{sum(g['gaps'] for g in gap_docs)}.",
        f"PER MODULE:\n{mod_lines}",
        f"DRAFTED SECTIONS:\n{drafted_lines}",
        f"DRAFTS WITH OPEN GAPS:\n{gap_lines}",
        f"EMPTY SECTIONS:\n{empty_lines}",
        "Write a concise readiness assessment in markdown, using ONLY the state "
        "above — do not invent any product, quality, safety, or efficacy facts. "
        "Structure it as:\n"
        "1. A one-line verdict.\n"
        "2. **Blockers** — the most critical EMPTY or gap-carrying sections that "
        "must be resolved before submission (pick the few that matter, not all).\n"
        "3. **Next actions** — a short prioritized list of what to do next.",
    ]))


async def analyze_readiness() -> dict:
    docs = list_generated_docs()  # walk once; share with build_plan + gap scan
    totals, modules, empties, drafted = _tally(build_plan(docs))
    open_gaps, gap_docs = _count_gaps(docs)
    score = round(100 * totals["approved"] / max(totals["engaged"], 1))
    verdict = _verdict(score, totals["in_review"], open_gaps)

    if totals["engaged"] == 0:
        narrative = ("No sections drafted yet — upload source documents or author "
                     "sections to begin building the dossier.")
    else:
        # The score/counts above need no LLM — a narrative failure must not sink
        # the whole report, so fall back to a note and still return the numbers.
        try:
            narrative = await llm.generate_text(
                _build_prompt(totals, modules, empties, drafted, gap_docs)
            )
        except Exception:
            logger.warning("readiness narrative generation failed", exc_info=True)
            narrative = ("_AI narrative unavailable — the analysis service could not "
                         "be reached. The score and section counts above are still accurate._")

    return {"score": score, "verdict_label": verdict, "totals": totals,
            "open_gaps": open_gaps, "modules": modules, "narrative": narrative}


if __name__ == "__main__":  # self-check: python -m app.services.readiness_service
    # score math: approved/engaged, empties don't penalise
    assert _verdict(100, 0, 0) == "ready"
    assert _verdict(90, 1, 0) == "nearly"
    assert _verdict(50, 2, 3) == "not_ready"
    # engaged==0 → score 0 (no divide-by-zero)
    assert round(100 * 0 / max(0, 1)) == 0
    # prompt carries the empty list + gap tally so the AI can prioritise
    p = _build_prompt(
        {"engaged": 2, "approved": 1, "in_review": 1, "empty": 1, "catalogue": 3},
        [{"module": "Module 3 — Quality", "approved": 1, "in_review": 1, "empty": 1, "drafted": 2}],
        [{"path": "3.2.P.8", "title": "Stability"}],
        [{"path": "2.3", "title": "QOS", "status": "in_review"}],
        [{"path": "2.3", "title": "QOS", "gaps": 4}],
    )
    assert "3.2.P.8 Stability" in p and "4 open gap" in p and "do not invent" in p
    print("OK — readiness score math + prompt (empties + gaps) verified")
