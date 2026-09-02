"""PostgreSQL-backed dossier placement and tree listing.

Multiple dossiers live side by side in the `dossiers` table, one row per
dossier (its `dossier_id`). Every function below that reads or writes dossier
content takes that dossier's root Path explicitly — there is no process-wide
"current dossier" global, so concurrent requests for different dossiers never
interfere with each other.

The root/section_dir Path arguments are opaque handles (they never need to
exist on disk): `root.name` is the dossier id, and a section handle is always
`<root>/<module_dir>/<section_dir>`. All state lives in the Document/Dossier
tables via app.services.db_repo — see that module for the handle→key mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services import db_repo
from app.services.dossier_validation import (
    _safe_dir_name,
    _safe_filename,
    _safe_path_part,
    slugify,
)

_DOSSIERS_ROOT = Path(settings.DOSSIERS_ROOT)

# Review states for generated CTD documents.
STATUS_DRAFT = "draft"
STATUS_EDITED = "edited"
STATUS_APPROVED = "approved"
VALID_STATUSES = {STATUS_DRAFT, STATUS_EDITED, STATUS_APPROVED}

__all__ = [
    "STATUS_DRAFT", "STATUS_EDITED", "STATUS_APPROVED", "VALID_STATUSES",
    "_safe_dir_name", "_safe_filename", "_safe_path_part", "slugify",
    "dossier_root", "dossier_summary", "list_dossiers", "get_dossier",
    "create_dossier", "_resolve_section_dir", "read_status", "write_generated",
    "read_generated", "read_meta", "write_fields", "load_extracted_text",
    "list_generated_docs", "build_plan", "read_context", "write_context",
    "context_block", "create_section_document", "reclassify_document",
    "file_into_dossier", "tree",
]


def dossier_root(dossier_id: str) -> Path:
    """Resolve a dossier_id to its root Path handle (does not touch disk)."""
    safe_id = _safe_path_part(dossier_id)
    return _DOSSIERS_ROOT / safe_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dossier_summary(root: Path) -> dict:
    """Lightweight card data for the dossier picker: id, name, product, counts."""
    dossier_id = db_repo.dossier_id_from_root(root)
    row = db_repo.get_dossier_row(dossier_id)
    docs = db_repo.list_documents(dossier_id)
    generated = [d for d in docs if (d.generated_markdown or "").strip()]
    context = (row.context if row else None) or {}
    return {
        "id": dossier_id,
        "name": (row.name if row else "") or dossier_id,
        "product_name": context.get("product_name", ""),
        "created_at": row.created_at.isoformat() if row else "",
        "filed": len(generated),
        "approved": sum(1 for d in generated if d.status == STATUS_APPROVED),
    }


def list_dossiers() -> list[dict]:
    """Every dossier, newest first."""
    from app.db import Dossier, session_scope
    from sqlalchemy import select

    with session_scope() as session:
        rows = list(session.execute(
            select(Dossier).order_by(Dossier.created_at.desc())
        ).scalars())
    return [dossier_summary(dossier_root(r.id)) for r in rows]


def get_dossier(dossier_id: str) -> dict | None:
    """Return the dossier's summary, or None if it doesn't exist."""
    if db_repo.get_dossier_row(_safe_path_part(dossier_id)) is None:
        return None
    return dossier_summary(dossier_root(dossier_id))


def create_dossier(name: str) -> dict:
    """Create a new, empty dossier and return its summary."""
    name = name.strip() or "Untitled Dossier"
    base_slug = slugify(name)
    slug = db_repo.unique_slug(base_slug)
    db_repo.ensure_dossier_row(slug, name=name)
    return dossier_summary(dossier_root(slug))


def _resolve_section_dir(root: Path, path_param: str) -> Path:
    """Convert a slash-separated dossier path into a verified section handle.

    path_param format: '<module>/<section folder>', e.g.
    'Module 3 — Quality/3.2.P.8.1 Stability Summary and Conclusion (Drug Product)'.
    """
    if not path_param:
        raise ValueError("Empty section_path")
    parts = [p.strip() for p in path_param.split("/") if p.strip()]
    if len(parts) != 2:
        raise ValueError(f"section_path must be module/section: {path_param!r}")
    module_part = _safe_path_part(parts[0])
    section_part = _safe_path_part(parts[1])
    return Path(root) / module_part / section_part


def _status_dict(row) -> dict:
    """Normalized review-status payload for a Document row (or None)."""
    data = {
        "status": (row.status if row else None) or STATUS_DRAFT,
        "updated_at": row.updated_at.isoformat() if row else _now_iso(),
        "feedback_history": (row.feedback_history if row else None) or [],
    }
    if data["status"] not in VALID_STATUSES:
        data["status"] = STATUS_DRAFT
    return data


def read_status(section_dir: Path, stem: str) -> dict:
    """Return the review status for a stem."""
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    return _status_dict(row)


def write_generated(section_dir: Path, stem: str, markdown: str, status: str = STATUS_DRAFT, feedback_history: list | None = None) -> None:
    """Persist an AI-authored document and update its review status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    if feedback_history is None:
        feedback_history = (row.feedback_history if row else None) or []
    db_repo.upsert_document(
        dossier_id, section_path, safe_stem,
        generated_markdown=markdown, status=status, feedback_history=feedback_history,
    )


def read_generated(section_dir: Path, stem: str) -> str:
    """Return the generated markdown for a stem, or '' if missing."""
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    return (row.generated_markdown or "") if row else ""


def read_meta(section_dir: Path, stem: str) -> dict:
    """Return classification metadata for a stem, or {} if missing."""
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    return dict(row.meta or {}) if row else {}


def write_fields(section_dir: Path, stem: str, fields: list[dict]) -> None:
    """Persist extracted structured fields into the document's meta."""
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    if db_repo.update_document_fields(dossier_id, section_path, safe_stem, meta_patch={"fields": fields}) is None:
        raise FileNotFoundError(f"No document found at {section_dir}/{safe_stem}")


def load_extracted_text(section_dir: Path, meta: dict) -> str:
    """Return the document's extracted text, preferring the stored copy.

    Falls back to re-running the OCR pipeline on the original bytes only for
    documents filed before extracted_text was persisted.
    """
    text = meta.get("extracted_text", "")
    if text:
        return text
    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, meta.get("stem", "section"))
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    if row is None:
        return ""
    if row.extracted_text:
        return row.extracted_text
    if row.original_data and row.filename:
        from app.services.document_processor import DocumentProcessor

        return DocumentProcessor().process(row.original_data, row.filename).full_text
    return ""


def list_generated_docs(root: Path) -> list[dict]:
    """Return every generated document + status across one dossier."""
    dossier_id = db_repo.dossier_id_from_root(root)
    docs: list[dict] = []
    for row in db_repo.list_documents(dossier_id):
        if not (row.generated_markdown or "").strip():
            continue
        status = _status_dict(row)
        meta = row.meta or {}
        docs.append(
            {
                "section_path": row.section_path,
                "stem": row.stem,
                "filename": row.filename or meta.get("filename", ""),
                "title": row.title or meta.get("title", ""),
                "module": row.module or meta.get("module", ""),
                # Bare CTD path (e.g. "3.2.P.8.3") — lets the plan builder map a
                # filed document back onto its section in the CTD catalogue.
                "ctd_path": row.ctd_path or meta.get("section_path", ""),
                "status": status["status"],
                "updated_at": status["updated_at"],
                "feedback_count": len(status.get("feedback_history", [])),
            }
        )
    return docs


def build_plan(root: Path, docs: list[dict] | None = None) -> list[dict]:
    """Merge the full CTD catalogue with filed documents into a completion map.

    Every CTD section is returned (even with no document), grouped by module,
    each carrying a rollup status: 'approved' (all its docs approved),
    'in_review' (has docs, not all approved), or 'empty' (no document yet).

    Pass `docs` (a prior list_generated_docs() result) to avoid re-querying
    when the caller already has it.
    """
    from collections import defaultdict

    from app.services.ctd_map import CTD_MAP, MODULE_NAMES

    if docs is None:
        docs = list_generated_docs(root)
    docs_by_path: dict[str, list] = defaultdict(list)
    for d in docs:
        docs_by_path[d["ctd_path"]].append(d)

    modules: dict[str, list] = {}
    for path, title in CTD_MAP.items():
        module = MODULE_NAMES.get(path.split(".")[0], "Other")
        path_docs = docs_by_path.get(path, [])
        if not path_docs:
            status = "empty"
        elif all(x["status"] == "approved" for x in path_docs):
            status = "approved"
        else:
            status = "in_review"
        modules.setdefault(module, []).append(
            {"path": path, "title": title, "status": status, "documents": path_docs}
        )
    return [{"module": m, "sections": secs} for m, secs in modules.items()]


def read_context(root: Path) -> dict:
    """Return a dossier's product context as {str: str}, or {} if none saved.

    Values are coerced to strings so a corrupt/hand-edited row can never break
    ProductContext validation or prompt formatting downstream.
    """
    dossier_id = db_repo.dossier_id_from_root(root)
    row = db_repo.get_dossier_row(dossier_id)
    data = (row.context if row else None) or {}
    if not isinstance(data, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in data.items()}


def write_context(root: Path, data: dict) -> None:
    """Persist a dossier's product context."""
    from app.db import Dossier, session_scope

    dossier_id = db_repo.dossier_id_from_root(root)
    db_repo.ensure_dossier_row(dossier_id)
    with session_scope() as session:
        row = session.get(Dossier, dossier_id)
        row.context = dict(data)


def context_block(root: Path, header: str) -> str:
    """Format a dossier's saved product context as a prompt block, or '' if empty."""
    filled = {k: v for k, v in read_context(root).items() if isinstance(v, str) and v.strip()}
    if not filled:
        return ""
    lines = [f"- {k.replace('_', ' ').title()}: {v.strip()}" for k, v in filled.items()]
    return header + "\n" + "\n".join(lines)


def create_section_document(root: Path, ctd_path: str, title: str, module: str, stem: str = "section") -> dict:
    """Create (idempotently) an authored-document scaffold for a CTD section
    that has no uploaded source, so it can be edited/generated/approved like any
    filed document. Returns {section_dir, stem, section_path (folder rel)}.
    """
    safe_stem = _safe_filename(stem)
    module_dir = _safe_dir_name(module)
    section_dir_name = _safe_dir_name(f"{ctd_path} {title}")
    section_dir = db_repo.section_handle(root, module_dir, section_dir_name)
    section_path = f"{module_dir}/{section_dir_name}"
    dossier_id = db_repo.dossier_id_from_root(root)

    if db_repo.get_document_row(dossier_id, section_path, safe_stem) is None:
        db_repo.upsert_document(
            dossier_id, section_path, safe_stem,
            module=module, ctd_path=ctd_path, title=title,
            filename="",  # authored, no uploaded source
            meta={
                "filename": "",
                "section_path": ctd_path,
                "title": title,
                "module": module,
                "confidence": 1.0,
                "justification": "Authored directly in the review workspace.",
                "summary": "",
                "key_points": [],
                "extracted_chars": 0,
                "extracted_text": "",
                "pages": [],
                "had_ocr": False,
                "fields": [],
                "uploaded_at": _now_iso(),
                "stem": safe_stem,
            },
        )

    return {
        "section_dir": section_dir,
        "stem": safe_stem,
        "section_path": section_path,
    }


def reclassify_document(root: Path, section_dir: Path, stem: str, ctd_path: str, title: str, module: str) -> dict:
    """Move a filed document into a new CTD section, rewriting its
    classification. Returns {section_path, stem} — the new folder path and stem.
    """
    from app.db import Document, session_scope
    from sqlalchemy import delete, select

    dossier_id, section_path, safe_stem = db_repo.doc_key(section_dir, stem)
    row = db_repo.get_document_row(dossier_id, section_path, safe_stem)
    if row is None:
        raise FileNotFoundError(f"No document found at {section_dir}/{stem}")
    meta = dict(row.meta or {})

    new_module_dir = _safe_dir_name(module)
    new_section_dir_name = _safe_dir_name(f"{ctd_path} {title}")
    new_section_path = f"{new_module_dir}/{new_section_dir_name}"

    meta["section_path"], meta["title"], meta["module"] = ctd_path, title, module
    shared = {
        "module": module, "ctd_path": ctd_path, "title": title,
        "filename": row.filename, "original_data": row.original_data,
        "extracted_text": row.extracted_text, "pages": row.pages,
        "meta": meta, "generated_markdown": row.generated_markdown,
        "status": row.status, "feedback_history": row.feedback_history,
        "translations": row.translations,
    }
    # A document already in the target section is replaced (last wins).
    with session_scope() as session:
        session.execute(delete(Document).where(
            Document.dossier_id == dossier_id,
            Document.section_path == new_section_path,
            Document.stem == safe_stem,
        ))
    db_repo.upsert_document(dossier_id, new_section_path, safe_stem, **shared)
    if new_section_path != section_path:
        with session_scope() as session:
            session.execute(delete(Document).where(
                Document.dossier_id == dossier_id,
                Document.section_path == section_path,
                Document.stem == safe_stem,
            ))

    return {"section_path": new_section_path, "stem": safe_stem}


def file_into_dossier(root: Path, file_bytes, filename, classification, extracted_text, chunks: list[dict] | None = None) -> dict:
    """Store file and metadata under <module>/<section> for the dossier."""
    name = _safe_filename(filename)
    stem = Path(name).stem

    module = classification["module"]
    ctd_section_path = classification["section_path"]
    title = classification["title"]

    module_dir = _safe_dir_name(module)
    section_dir_name = _safe_dir_name(f"{ctd_section_path} {title}")
    section_path = f"{module_dir}/{section_dir_name}"
    section_dir = db_repo.section_handle(root, module_dir, section_dir_name)
    dossier_id = db_repo.dossier_id_from_root(root)

    db_repo.ensure_dossier_row(dossier_id)
    meta = {
        "filename": name,
        "section_path": ctd_section_path,
        "title": title,
        "module": module,
        "confidence": classification["confidence"],
        "justification": classification.get("justification", ""),
        "summary": classification.get("summary", ""),
        "key_points": classification.get("key_points", []),
        "extracted_chars": len(extracted_text),
        # Persist the full extracted text so regeneration/feedback never has to
        # re-run the (slow, paid) OCR pipeline on the original file.
        "extracted_text": extracted_text,
        # Page-indexed chunks [{page, text, is_ocr}] — powers the source viewer
        # and per-field page citations. Empty for documents filed before this.
        "pages": chunks or [],
        "had_ocr": any(c.get("is_ocr") for c in (chunks or [])),
        "fields": [],
        "uploaded_at": _now_iso(),
        "stem": stem,
    }
    db_repo.upsert_document(
        dossier_id, section_path, stem,
        module=module, ctd_path=ctd_section_path, title=title, filename=name,
        original_data=file_bytes, extracted_text=extracted_text,
        pages=chunks or [], meta=meta, status=STATUS_DRAFT,
    )

    return {
        "folder": f"{module}/{ctd_section_path} {title}",
        "path": str(section_dir / name),
        "section_path": ctd_section_path,
        # Folder-relative path (sanitized dir names) — what the API's
        # section_path query param and the frontend route actually need.
        "folder_path": section_path,
        "section_dir": section_dir,
        "stem": stem,
    }


def tree(root: Path) -> list[dict]:
    """Group the dossier's filed documents into a module/section/document tree."""
    dossier_id = db_repo.dossier_id_from_root(root)
    modules: dict[str, dict] = {}  # module_dir name → {"module": display, "sections": {}}
    for row in db_repo.list_documents(dossier_id):
        if not row.filename:  # authored sections have no source file → not listed
            continue
        module_dir, section_dir_name = row.section_path.split("/", 1)
        first_space = section_dir_name.find(" ")
        if first_space > 0:
            spath = section_dir_name[:first_space]
            stitle = section_dir_name[first_space + 1:]
        else:
            spath = section_dir_name
            stitle = ""

        meta = row.meta or {}
        document = {
            "name": row.filename,
            "confidence": meta.get("confidence", 0.0),
            "uploaded_at": meta.get("uploaded_at")
            or (row.uploaded_at.isoformat() if row.uploaded_at else ""),
        }
        module_entry = modules.setdefault(
            module_dir, {"module": row.module or module_dir, "sections": {}}
        )
        section_entry = module_entry["sections"].setdefault(
            section_dir_name, {"section_path": spath, "title": stitle, "documents": []}
        )
        section_entry["documents"].append(document)

    result = []
    for module_dir in sorted(modules):
        entry = modules[module_dir]
        sections = []
        for section_dir_name in sorted(entry["sections"]):
            section = entry["sections"][section_dir_name]
            section["documents"].sort(key=lambda d: d["name"])
            sections.append(section)
        result.append({"module": entry["module"], "sections": sections})
    return result
