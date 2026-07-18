# Plan: Dossier Generation → Review → Export

Implements `specs/dossier-generation-review-export.md`. Demo-scoped: filesystem
persistence, no DB, Markdown source of truth, DOCX export.

Locked defaults (from spec Open Questions):
1. Export = DOCX only (`python-docx`).
2. One generated document per uploaded file.
3. AI feedback regenerates from the current draft + original extracted text.
4. Generation runs automatically during `/process` (slice 1); review UI reads it after.

## Components & dependencies
```
generation_service (llm.py)          ─┐
dossier_service additions (fs I/O)   ─┼─→ dossier routes ─→ frontend/app/review ─→ export_service
schemas (models)                     ─┘
```
- `generation_service` depends only on existing `llm.py` + `ctd_map`.
- `dossier_service` additions depend on existing path-safety helpers.
- Routes depend on both + schemas.
- Review UI depends on routes.
- Export depends on the persisted `.generated.md`.

## Build order (vertical slices, each demoable)
1. **Generate + persist** — `generation_service`, `.generated.md`/`.status.json`, hook into `documents.py process`.
2. **Review read API + UI** — `GET /documents`, `GET /document`, `frontend/app/review` list+view.
3. **Manual edit** — `PUT /document`, editable textarea.
4. **AI feedback regenerate** — `POST /feedback`, feedback box.
5. **Approve + export** — `POST /approve`, `export_service`, `GET /export[/all]`, download.

## Risks & mitigations
- **Generation slows upload** (auto during process). → Run it after filing; if too slow in demo, flip to on-demand button (slice 2 already gives the trigger point). Reversible.
- **Path traversal** via section_path/stem in new endpoints. → Every route resolves through `_safe_dir_name`/`_safe_filename` and asserts the resolved path is under `DOSSIER_ROOT`. Covered by a self-check.
- **DOCX dep weight.** → `python-docx` is pure-python, no system libs. PDF deferred to avoid heavier deps (Open Question 1).
- **Regenerate destroys hand edits.** → Prior draft pushed to `feedback_history` before overwrite; never overwrite `approved` without explicit regenerate.
- **LLM truncation** on long section docs. → Leave `max_tokens` unset (fix already in `llm.py`).

## Parallelizable vs sequential
- Sequential spine: slice 1 → 2 → (3, 4 parallel) → 5.
- Within slice 1, `generation_service` and `dossier_service` sidecar I/O can be built in parallel, joined at the route.

## Verification checkpoints
- After slice 1: upload a file → `.generated.md` exists with correct CTD H1, self-checks pass.
- After slice 2: review page lists the draft and renders its markdown.
- After slice 3: edit persists, status → `edited`.
- After slice 4: feedback returns a changed draft, `feedback_history` grows.
- After slice 5: approved DOCX downloads with heading == CTD title; `export/all` bundles approved docs.
