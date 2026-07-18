# Spec: Dossier Document Generation → Review → Export

Status: DRAFT (awaiting human review)
Owner: Feyti / papermind
Scope: demo app — favor the smallest loop that proves the flow, not production hardening.

## Assumptions
Correct any of these now or implementation proceeds on them:
1. **Persistence stays filesystem-backed** (`DOSSIER_ROOT/<module>/<section>/`), reusing `dossier_service.py`. No database is introduced for the demo.
2. **Generated documents are Markdown** (`.generated.md`) — editable as plain text, diffable, and convertible to PDF/DOCX on export. Not authoring PDFs directly.
3. **One generated document per filed source document** (the uploaded file → its AI-authored CTD section write-up), living beside the original in the same section folder.
4. **Review state is per-document JSON**, not a workflow engine: `draft → edited → approved`.
5. **AI feedback regenerates the whole document** for that section (feedback + original extracted text + prior draft as context). No paragraph-level patching for the demo.
6. Single user, no auth/concurrency concerns for the demo.

## Objective
Today the pipeline ingests a document, classifies it into a CTD section, and files the **original** file + metadata. The end goal is a reviewable authoring loop:

1. **Generate** a properly-titled, CTD-structured document for each filed source.
2. **Review** generated documents in the UI instead of trusting output blindly.
3. **Correct** either by manual edit or by giving AI feedback that regenerates the document.
4. **Approve & Export** — download the reviewed documents (single file or whole dossier).

Success = a user can upload → see a generated section document → edit it or tell the AI "fix X" and get an updated draft → mark approved → download it.

## Tech Stack
- Backend: FastAPI (Python 3.14, `uv`), existing `llm.py` (Gemini/DeepSeek) for generation.
- Frontend: Next.js 16.2 / React 19, existing upload UI in `app/page.tsx`.
- Storage: filesystem under `DOSSIER_ROOT` (existing `dossier_service.py`).
- Export: Markdown → DOCX/PDF. Prefer a single already-installed or lightweight path (see Open Questions).

## Commands
```
Backend dev:   cd backend && uv run fastapi dev main.py
Backend check: cd backend && uv run python -m app.services.ctd_map   # module self-checks
Frontend dev:  cd frontend && npm run dev
Lint (fe):     cd frontend && npm run lint
```

## Project Structure
```
backend/app/api/routes/
  documents.py        → upload + process (exists) — extend to trigger generation
  dossier.py          → GET /tree (exists) — add review/edit/regenerate/export endpoints
backend/app/services/
  dossier_service.py  → filesystem placement + tree (exists) — add read/write/status/list-for-review
  generation_service.py   → NEW: author a CTD section document from extracted text + classification
  export_service.py       → NEW: Markdown → DOCX/PDF
backend/app/models/schemas.py → add GeneratedDoc / ReviewStatus / FeedbackRequest models
frontend/app/review/    → NEW: review UI (list drafts, view, edit, feedback, approve, download)
specs/                  → this spec
```

### On-disk layout (per section folder, extends current)
```
DOSSIER_ROOT/<module>/<section> <title>/
  <stem>.<ext>            # original upload (exists)
  <stem>.meta.json        # classification metadata (exists)
  <stem>.generated.md     # NEW: AI-authored document (the review target)
  <stem>.status.json      # NEW: {status, updated_at, feedback_history[]}
```

## Code Style
Match existing services: module docstring, `from __future__ import annotations`, small pure-ish functions, filesystem via `pathlib`, JSON sidecars. Example:

```python
def write_generated(section_dir: Path, stem: str, markdown: str) -> None:
    """Persist an AI-authored document and mark it a fresh draft."""
    (section_dir / f"{stem}.generated.md").write_text(markdown)
    _write_status(section_dir, stem, status="draft")
```

Reuse `_safe_filename` / `_safe_dir_name` from `dossier_service.py` — do not re-implement path sanitization.

## API (new endpoints)
```
POST /api/v1/dossier/generate        {section_path, stem}  → generate/regenerate a draft
GET  /api/v1/dossier/documents       → list generated docs + status (review queue)
GET  /api/v1/dossier/document        ?section_path&stem → {markdown, status, meta}
PUT  /api/v1/dossier/document        {section_path, stem, markdown} → manual edit → status=edited
POST /api/v1/dossier/feedback        {section_path, stem, feedback} → AI regenerate with feedback
POST /api/v1/dossier/approve         {section_path, stem} → status=approved
GET  /api/v1/dossier/export          ?section_path&stem&format=docx|pdf → file download
GET  /api/v1/dossier/export/all      ?format=docx|pdf → whole approved dossier as a zip/bundle
```
Path safety: every endpoint resolves the target via `_safe_dir_name`/`_safe_filename` and confirms the resolved path is inside `DOSSIER_ROOT` before read/write.

## Testing Strategy
Demo-level, no framework sprawl. Each new service ships one `__main__` self-check (assert-based), matching `ctd_map.py`'s pattern:
- `generation_service`: given canned extracted text + classification, returns non-empty markdown whose H1 == the CTD title.
- `dossier_service` additions: write → read round-trips markdown and status; path traversal (`../`) is rejected.
- `export_service`: markdown → non-empty DOCX/PDF bytes.
Manual check: upload → generate → edit → feedback → approve → download, end to end (the `/run` or `/verify` skill).

## Boundaries
- **Always:** sanitize section_path/stem and confine writes to `DOSSIER_ROOT`; keep the generated `.md` the single editable source of truth; leave `max_tokens` unset on generation calls (avoid the truncation bug fixed in `llm.py`).
- **Ask first:** adding a database or ORM; adding a heavy export dependency (LibreOffice, weasyprint) vs. a pure-python one; changing the classification/section-map behavior.
- **Never:** commit `DOSSIER_ROOT` contents or secrets; overwrite an `approved` document without an explicit regenerate; delete a user's manual edits on regenerate without preserving the prior draft in `feedback_history`.

## Success Criteria
1. After upload+process, a `.generated.md` exists in the section folder with the correct CTD H1 title (no `[placeholder]` text).
2. `GET /dossier/documents` returns every generated doc with a `status`.
3. Editing via `PUT` persists and flips status to `edited`; reopening returns the edited text.
4. `POST /feedback` with "make the summary shorter" returns a changed draft and appends to `feedback_history`.
5. `POST /approve` flips status to `approved`.
6. `GET /export?format=docx` downloads a DOCX whose heading matches the CTD title; `export/all` bundles all approved docs.
7. All new-service `__main__` self-checks pass; manual end-to-end loop works.

## Implementation Slices (build in this order; each is independently demoable)
1. **Generate + persist** — `generation_service` + `.generated.md`/`.status.json` + `POST /generate`; wire into `documents.py` process. (proves step 1)
2. **Review read API + UI list/view** — `GET /documents`, `GET /document`, `frontend/app/review`. (proves step 2)
3. **Manual edit** — `PUT /document`, editable textarea + save. (proves step 3a)
4. **AI feedback regenerate** — `POST /feedback`, feedback box + regenerate. (proves step 3b)
5. **Approve + export** — `POST /approve`, `export_service`, `GET /export[/all]`, download button. (proves steps 4–5)

## Open Questions
1. **Export format priority** — DOCX, PDF, or both for the demo? (DOCX via `python-docx` is the lightest; PDF usually needs a heavier dep.)
2. **Generation granularity** — one document per uploaded file (assumed), or one merged document per CTD section when multiple files land in the same section?
3. **Regenerate vs. original** — should AI feedback regeneration always start from the original extracted text, or iterate on the current (possibly hand-edited) draft?
4. **"Generate" trigger** — automatic during `/process` (slower upload), or an explicit button in the review UI (assumed: auto in slice 1, revisit)?
```
