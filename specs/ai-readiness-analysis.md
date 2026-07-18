# AI Readiness Analysis

**Goal:** one click on the review page tells the user how ready their CTD dossier
is to submit — a trustworthy structural score plus an AI-written verdict, top
blockers, and prioritized next actions.

**Scope (chosen):** structural completeness + single AI narrative pass. No
per-section content critique in v1. Surfaces as a panel on the existing review
page (no new route).

---

## Design principle: the numbers are deterministic, the AI only narrates

The score, counts, and gap tally come from data we already have. The LLM never
produces a number and never invents regulatory facts — it reasons over the
completion state we hand it and writes prose. This keeps the readiness figure
honest and the AI call cheap (one call) and un-parseable-failure-proof (markdown
out, no JSON to break).

### The denominator problem (the one real design decision)

The CTD catalogue is **301 sections**, but any given product only fills a
subset. `approved / 301` would read ~11% forever and be meaningless.

**Score = approved / engaged**, where *engaged* = sections with ≥1 document
(`approved` + `in_review`). Reads as: "of the sections you've started, X% are
signed off." `empty` sections are reported as *coverage* (informational), not as
a readiness penalty. **Which empty sections actually matter is the AI's job** —
it sees the empty list + product context and flags the critical omissions (e.g.
"3.2.P.8 Stability empty", "2.7 Clinical Summary missing"). Judgment stays with
the model; arithmetic stays deterministic.

---

## Backend

### New: `backend/app/services/readiness_service.py`

Builds entirely on existing helpers — `build_plan()`, `list_generated_docs()`,
`read_generated()`, `context_block()`, `GAP_MARKER`, `llm.generate_text`.

```
async def analyze_readiness() -> dict:
    plan = build_plan()                       # every section + rollup status
    # 1. tally per module + overall
    #    per section status in {approved, in_review, empty}
    # 2. scan gap markers: for each generated doc, count GAP_MARKER occurrences
    #    (rglob *.generated.md via list_generated_docs + read_generated)
    #    ponytail: reads every drafted doc; fine for a demo, memoize by mtime if it bites
    # 3. score = round(100 * approved / max(approved + in_review, 1))
    #    verdict_label (deterministic):
    #      "ready"      if score==100 and in_review==0 and open_gaps==0
    #      "nearly"     if score>=80
    #      "not_ready"  otherwise
    # 4. AI narrative: one generate_text call. Prompt = product context
    #    + compact completion summary (per-module counts, empty section
    #    paths+titles capped, drafted sections w/ gap counts). Ask for markdown:
    #    a one-line verdict, "Blockers" bullets, "Next actions" bullets.
    #    Instruction: base ONLY on this data, do not invent facts.
    return {score, verdict_label, totals, open_gaps, modules[], narrative}
```

`totals = {approved, in_review, empty, engaged, catalogue}`
`modules[] = {module, approved, in_review, empty, drafted}`

Self-check (`__main__`): assert score math on a fake plan (0 engaged → 0, all
approved → 100), and that the prompt carries the empty-section list + gap count.
Stub `generate_text` so no network in the check.

### New endpoint: `GET /api/v1/dossier/readiness`

```
@router.get("/readiness", response_model=ReadinessReport)
async def readiness():
    return await analyze_readiness()
```

Async, button-triggered, so the one LLM call's latency is fine. No inputs — it
reads the whole dossier state.

### Schemas (`schemas.py`)

```
class ModuleReadiness(BaseModel):
    module: str
    approved: int; in_review: int; empty: int; drafted: int

class ReadinessReport(BaseModel):
    score: int                 # 0..100, approved/engaged
    verdict_label: str         # ready | nearly | not_ready
    totals: dict               # approved/in_review/empty/engaged/catalogue
    open_gaps: int             # total ⚠️ TO BE PROVIDED markers across drafts
    modules: list[ModuleReadiness]
    narrative: str             # AI markdown: verdict + blockers + next actions
```

---

## Frontend (`app/review/page.tsx`)

- **`⚡ Readiness` button** in the review toolbar/header.
- On click → `setReadinessLoading`, `GET /dossier/readiness`, open a panel
  (right pane, same slot the new-section panel uses).
- Panel renders, reusing existing components:
  - Big **score** + **verdict Pill** (colour by `verdict_label`).
  - Totals row: approved / in review / empty / open gaps.
  - Per-module mini bars (approved vs drafted vs empty) — plain flex divs, no
    chart lib.
  - **AI narrative** via the markdown renderer already used for documents.
- State: `readiness`, `readinessLoading`. No new deps, no new route, no nav.

---

## What's deliberately skipped (add when asked)

- **Per-section AI content critique** (reading each draft's text for weak/thin/
  contradictory content) — the heavier "Depth" option; one LLM call per doc.
- **Per-product required-section set** (a real submission checklist) — would let
  the score gate on *required* rather than *engaged* sections. Needs a
  region/product → required-paths map we don't have. AI narrative covers the
  "what's critically missing" need for now.
- **Caching the report** — recomputed on each click. Trivial dossier size.

## Effort

~1 new backend file + 1 endpoint + 2 schemas; ~1 button + 1 panel + 2 state
vars on the review page. Everything else is reuse.
