# PaperMind — Agent Instructions

Feyti regulatory document intelligence demo. Users upload PDF/DOCX, the app extracts text
(OCR if scanned), classifies it into an ICH-M4 CTD section with an LLM, and files it into a
live dossier. Next.js 16 frontend (Bun), FastAPI backend (Python 3.10, uv), no database —
filesystem persistence with JSON sidecars.

## Monorepo context

- `papermind/` — the demo app (this project). Backend in `backend/`, frontend in `frontend/`.
- `regulate-api-core/` — the full platform (Django). **Read-only source for porting**: proven
  feature modules live there; port pure-function services, never copy Django ORM models.
  - `adr/` — pharmacovigilance: `services/minimum_criteria.py`, `services/e2b.py` (E2B(R3)
    ICSR builder), `services/expectedness.py`, `services/deduplication.py`, `services/meddra.py`
  - `regulations_translation/` — `services/llm_translation.py` (chunked LLM translation)
  - `regintelligence/` — `services/african_crawlers.py` (authority crawlers),
    `services/change_detection.py`, `services/ai.py`
  - `lls/` — `scrapers/search_engines.py` (PubMed, Semantic Scholar, PLoS, Springer, BMC),
    `scrapers/pamj.py`, `scrapers/health_go_ug.py`, `services/search_intelligence.py`
- Active plan: `tasks/plan-2026-09-01-adr-multilingual-regintel-literature.md` — four features:
  PV/ADR reporting, multilingual (EN/FR/PT/SW), regulatory intelligence dashboard, local
  literature search. Work task-by-task in that file's order.

## Backend conventions (`backend/`)

- Python 3.10 + uv. Run tests: `uv run pytest tests/ -v`. Syntax gate: `uv run python -m compileall app main.py`.
- No DB. Persistence = JSON sidecar files inside `DOSSIERS_ROOT` (one folder per dossier).
  New stores must go through `app/services/store_utils.py` (`safe_join`, `read_json`, `write_json`)
  and respect `_safe_dir_name`/`_safe_filename` in `dossier_service.py`. Every path resolve
  must assert the result is under the dossier root (path traversal is the #1 risk).
- Per-document metadata: `<stem>.meta.json`; status: `<stem>.status.json`; generated content:
  `<stem>.generated.md`. Translated copies: `<stem>.<lang>.generated.md` (never overwrite originals).
- LLM calls go through `app/services/llm.py` only (`generate_json`, `generate_text`) —
  Aicyclinder → Kimi → Gemini fallback chain. Never call providers directly from feature code.
- Deterministic-first principle (from `specs/capability-buildout.md`): deterministic checks
  produce the numbers; the LLM only narrates, extracts, or translates. Every LLM feature must
  have a deterministic fallback and degrade gracefully when the LLM is unreachable.
- Routers register in `app/api/routes/__init__.py` under `settings.API_V1_STR`; new settings
  go in `app/core/config.py` (`Settings`). Tests are filesystem-fixture based, no network, no
  live LLM calls (mock `app.services.llm`).

## Frontend conventions (`frontend/`)

- Next.js 16, Bun, shadcn/ui, Tailwind. Verify with `bun run lint && bun run build`.
- Pages under `app/d/[dossierId]/`; shared helpers in `lib/api.ts` (`apiFetch`, `dossierApi`,
  `downloadFromApi`) — never hand-roll fetch/error handling per page.
- Nav lives in `components/nav.tsx` — every new page gets a nav entry.
- UI strings for new features come from `lib/i18n.ts` dictionaries (EN/FR/PT/SW), consumed via
  `useLanguage()`.

## Git

- `papermind/` is its own git repo (branch `main`). Commit after every task:
  `git add <files> && git commit -m "feat(papermind): <description>"`.
- Do not touch `regulate-api-core/`, `app.regulateapi.com/`, or `feyti-ocr/` — read-only.
