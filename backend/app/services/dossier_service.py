"""Filesystem-backed dossier placement and tree listing.

Multiple dossiers live side by side under DOSSIERS_ROOT, one directory per
dossier (its `dossier_id`). Every function below that reads or writes dossier
content takes that dossier's resolved root Path explicitly — there is no
process-wide "current dossier" global, so concurrent requests for different
dossiers never interfere with each other.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_DOSSIERS_ROOT = Path(settings.DOSSIERS_ROOT)

# Review states for generated CTD documents.
STATUS_DRAFT = "draft"
STATUS_EDITED = "edited"
STATUS_APPROVED = "approved"
VALID_STATUSES = {STATUS_DRAFT, STATUS_EDITED, STATUS_APPROVED}


def _safe_filename(filename: str) -> str:
    """Return a safe basename; reject path separators and parent references."""
    name = os.path.basename(filename)
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError("Invalid filename")
    return name


def _safe_dir_name(text: str) -> str:
    """Replace filesystem-hostile characters with underscores."""
    # Keep letters, numbers, spaces, dots, dashes; swap slashes / backslashes.
    return "".join(c if c.isalnum() or c in " .-_" else "_" for c in text).strip()


def _safe_path_part(text: str) -> str:
    """Return a single path component; reject separators and parent refs."""
    if not text or ".." in text or "/" in text or "\\" in text:
        raise ValueError(f"Invalid path component: {text!r}")
    return text


def slugify(name: str) -> str:
    """Turn a display name into a URL/filesystem-safe id."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "dossier"


def dossier_root(dossier_id: str) -> Path:
    """Resolve a dossier_id to its root Path (does not check existence)."""
    safe_id = _safe_path_part(dossier_id)
    return _DOSSIERS_ROOT / safe_id


def _dossier_meta_path(root: Path) -> Path:
    return root / ".dossier.json"


def _context_path(root: Path) -> Path:
    return root / ".context.json"


def _migrate_legacy_dossier() -> None:
    """One-time move of the pre-multi-dossier layout (./dossier) into
    DOSSIERS_ROOT/default, so upgrading never loses already-filed work."""
    if _DOSSIERS_ROOT.exists():
        return
    legacy = Path(settings.LEGACY_DOSSIER_ROOT)
    if not legacy.exists() or not any(legacy.iterdir()):
        return
    _DOSSIERS_ROOT.mkdir(parents=True, exist_ok=True)
    new_root = _DOSSIERS_ROOT / "default"
    legacy.rename(new_root)
    name = read_context(new_root).get("product_name") or "Untitled Dossier"
    _dossier_meta_path(new_root).write_text(json.dumps({
        "id": "default", "name": name, "created_at": _now_iso(),
    }, indent=2))


def dossier_summary(root: Path) -> dict:
    """Lightweight card data for the dossier picker: id, name, product, counts."""
    meta = {}
    meta_path = _dossier_meta_path(root)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            meta = {}
    docs = list_generated_docs(root)
    approved = sum(1 for d in docs if d["status"] == STATUS_APPROVED)
    return {
        "id": meta.get("id", root.name),
        "name": meta.get("name") or root.name,
        "product_name": read_context(root).get("product_name", ""),
        "created_at": meta.get("created_at", ""),
        "filed": len(docs),
        "approved": approved,
    }


def list_dossiers() -> list[dict]:
    """Every dossier under DOSSIERS_ROOT, newest first."""
    _migrate_legacy_dossier()
    if not _DOSSIERS_ROOT.exists():
        return []
    summaries = [
        dossier_summary(d) for d in sorted(_DOSSIERS_ROOT.iterdir())
        if d.is_dir() and _dossier_meta_path(d).exists()
    ]
    return sorted(summaries, key=lambda s: s["created_at"], reverse=True)


def get_dossier(dossier_id: str) -> dict | None:
    """Return the dossier's summary, or None if it doesn't exist."""
    root = dossier_root(dossier_id)
    if not _dossier_meta_path(root).exists():
        return None
    return dossier_summary(root)


def create_dossier(name: str) -> dict:
    """Create a new, empty dossier and return its summary."""
    name = name.strip() or "Untitled Dossier"
    base_slug = slugify(name)
    slug = base_slug
    n = 2
    while (_DOSSIERS_ROOT / slug).exists():
        slug = f"{base_slug}-{n}"
        n += 1

    root = _DOSSIERS_ROOT / slug
    root.mkdir(parents=True)
    _dossier_meta_path(root).write_text(json.dumps({
        "id": slug, "name": name, "created_at": _now_iso(),
    }, indent=2))
    return dossier_summary(root)


def _resolve_section_dir(root: Path, path_param: str) -> Path:
    """Convert a slash-separated dossier path into a verified Path under root.

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
    section_dir = (root / module_part / section_part).resolve()
    resolved_root = root.resolve()
    if resolved_root not in section_dir.parents and section_dir != resolved_root:
        raise ValueError(f"Resolved path escapes dossier root: {section_dir}")
    if not section_dir.is_dir():
        raise ValueError(f"Section folder not found: {path_param}")
    return section_dir


def _status_path(section_dir: Path, stem: str) -> Path:
    return section_dir / f"{_safe_filename(stem)}.status.json"


def _generated_path(section_dir: Path, stem: str) -> Path:
    return section_dir / f"{_safe_filename(stem)}.generated.md"


def _meta_path(section_dir: Path, stem: str) -> Path:
    return section_dir / f"{_safe_filename(stem)}.meta.json"


def resolve_document_paths(root: Path, path_param: str, stem: str) -> dict:
    """Resolve section_path + stem to verified file paths under a dossier root.

    Returns {"section_dir": Path, "generated": Path, "status": Path, "meta": Path}.
    Raises ValueError for traversal attempts or paths outside the dossier.
    """
    section_dir = _resolve_section_dir(root, path_param)
    safe_stem = _safe_filename(stem)
    return {
        "section_dir": section_dir,
        "generated": _generated_path(section_dir, safe_stem),
        "status": _status_path(section_dir, safe_stem),
        "meta": _meta_path(section_dir, safe_stem),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_status(section_dir: Path, stem: str) -> dict:
    path = _status_path(section_dir, stem)
    if not path.exists():
        return {"status": STATUS_DRAFT, "updated_at": _now_iso(), "feedback_history": []}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        data = {}
    data.setdefault("status", STATUS_DRAFT)
    data.setdefault("updated_at", _now_iso())
    data.setdefault("feedback_history", [])
    if data["status"] not in VALID_STATUSES:
        data["status"] = STATUS_DRAFT
    return data


def _write_status(section_dir: Path, stem: str, status: str, feedback_history: list | None = None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    data = _read_status(section_dir, stem)
    data["status"] = status
    data["updated_at"] = _now_iso()
    if feedback_history is not None:
        data["feedback_history"] = feedback_history
    _status_path(section_dir, stem).write_text(json.dumps(data, indent=2))


def write_generated(section_dir: Path, stem: str, markdown: str, status: str = STATUS_DRAFT, feedback_history: list | None = None) -> None:
    """Persist an AI-authored document and update its review status."""
    _generated_path(section_dir, stem).write_text(markdown)
    _write_status(section_dir, stem, status, feedback_history=feedback_history)


def read_generated(section_dir: Path, stem: str) -> str:
    """Return the generated markdown for a stem, or '' if missing."""
    path = _generated_path(section_dir, stem)
    return path.read_text() if path.exists() else ""


def read_status(section_dir: Path, stem: str) -> dict:
    """Return the review status sidecar for a stem."""
    return _read_status(section_dir, stem)


def read_meta(section_dir: Path, stem: str) -> dict:
    """Return classification metadata for a stem, or {} if missing."""
    path = _meta_path(section_dir, stem)
    return json.loads(path.read_text()) if path.exists() else {}


def write_fields(section_dir: Path, stem: str, fields: list[dict]) -> None:
    """Persist extracted structured fields into the document's meta sidecar."""
    path = _meta_path(section_dir, stem)
    meta = json.loads(path.read_text()) if path.exists() else {}
    meta["fields"] = fields
    path.write_text(json.dumps(meta, indent=2))


def load_extracted_text(section_dir: Path, meta: dict) -> str:
    """Return the document's extracted text, preferring the stored copy.

    Falls back to re-running the OCR pipeline on the original file only for
    documents filed before extracted_text was persisted in meta.
    """
    text = meta.get("extracted_text", "")
    if text:
        return text
    filename = meta.get("filename")
    original = section_dir / filename if filename else None
    if original and original.exists():
        from app.services.document_processor import DocumentProcessor

        return DocumentProcessor().process(original.read_bytes(), original.name).full_text
    return ""


def list_generated_docs(root: Path) -> list[dict]:
    """Return every generated document + status across one dossier."""
    docs: list[dict] = []
    if not root.exists():
        return docs
    for generated in sorted(root.rglob("*.generated.md")):
        section_dir = generated.parent
        stem = generated.stem.replace(".generated", "")
        status = _read_status(section_dir, stem)
        meta = read_meta(section_dir, stem)
        rel = section_dir.relative_to(root)
        docs.append(
            {
                "section_path": str(rel),
                "stem": stem,
                "filename": meta.get("filename", ""),
                "title": meta.get("title", ""),
                "module": meta.get("module", ""),
                # Bare CTD path (e.g. "3.2.P.8.3") — lets the plan builder map a
                # filed document back onto its section in the CTD catalogue.
                "ctd_path": meta.get("section_path", ""),
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

    Pass `docs` (a prior list_generated_docs() result) to avoid re-walking the
    dossier when the caller already has it.
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


# Per-dossier product context cache, keyed by resolved root path string.
# (mtime, value); invalidated per-dossier when its context file changes.
_context_cache: dict[str, tuple[float, dict]] = {}


def read_context(root: Path) -> dict:
    """Return a dossier's product context as {str: str}, or {} if none saved.

    Values are coerced to strings so a hand-edited/corrupt file can never break
    ProductContext validation or prompt formatting downstream. Memoized by file
    mtime so classify()/generate() don't re-read the file on every call.
    """
    context_path = _context_path(root)
    key = str(root)
    if not context_path.exists():
        _context_cache.pop(key, None)
        return {}
    mtime = context_path.stat().st_mtime
    cached = _context_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        data = json.loads(context_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    value = {str(k): "" if v is None else str(v) for k, v in data.items()}
    _context_cache[key] = (mtime, value)
    return value


def write_context(root: Path, data: dict) -> None:
    """Persist a dossier's product context."""
    root.mkdir(parents=True, exist_ok=True)
    _context_path(root).write_text(json.dumps(data, indent=2))


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
    module_dir = root / _safe_dir_name(module)
    section_dir = module_dir / _safe_dir_name(f"{ctd_path} {title}")
    section_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / ".module.json").write_text(json.dumps({"module": module}))

    meta_path = _meta_path(section_dir, safe_stem)
    if not meta_path.exists():
        meta_path.write_text(json.dumps({
            "filename": "",  # authored, no uploaded source
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
        }, indent=2))

    return {
        "section_dir": section_dir,
        "stem": safe_stem,
        "section_path": str(section_dir.relative_to(root)),
    }


def reclassify_document(root: Path, section_dir: Path, stem: str, ctd_path: str, title: str, module: str) -> dict:
    """Move a filed document (source file + meta/status/generated sidecars)
    into a new CTD section folder, rewriting its classification in meta.
    Returns {section_path, stem} — the new folder path and stem.
    """
    meta_path = _meta_path(section_dir, stem)
    if not meta_path.exists():
        raise FileNotFoundError(f"No document found at {section_dir}/{stem}")
    meta = json.loads(meta_path.read_text())

    new_module_dir = root / _safe_dir_name(module)
    new_section_dir = new_module_dir / _safe_dir_name(f"{ctd_path} {title}")
    new_section_dir.mkdir(parents=True, exist_ok=True)
    (new_module_dir / ".module.json").write_text(json.dumps({"module": module}))

    meta["section_path"], meta["title"], meta["module"] = ctd_path, title, module
    meta_path.write_text(json.dumps(meta, indent=2))  # rewrite before move; path changes below

    for path_fn in (_meta_path, _status_path, _generated_path):
        src = path_fn(section_dir, stem)
        if src.exists():
            src.rename(path_fn(new_section_dir, stem))

    original = meta.get("filename")
    if original:
        src_file = section_dir / original
        if src_file.exists():
            src_file.rename(new_section_dir / original)

    return {
        "section_path": str(new_section_dir.relative_to(root)),
        "stem": stem,
    }


def file_into_dossier(root: Path, file_bytes, filename, classification, extracted_text, chunks: list[dict] | None = None) -> dict:
    """Write file and metadata under root/<module>/<section>."""
    name = _safe_filename(filename)
    stem = Path(name).stem

    module = classification["module"]
    section_path = classification["section_path"]
    title = classification["title"]

    module_dir = root / _safe_dir_name(module)
    section_dir = module_dir / _safe_dir_name(f"{section_path} {title}")
    section_dir.mkdir(parents=True, exist_ok=True)

    # Preserve the original display module name for tree().
    (module_dir / ".module.json").write_text(json.dumps({"module": module}))

    file_path = section_dir / name
    file_path.write_bytes(file_bytes)

    meta = {
        "filename": name,
        "section_path": section_path,
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
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    (section_dir / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2))

    return {
        "folder": f"{module}/{section_path} {title}",
        "path": str(file_path),
        "section_path": section_path,
        # Folder-relative path (sanitized dir names) — what the API's
        # section_path query param and the frontend route actually need.
        "folder_path": str(section_dir.relative_to(root)),
        "section_dir": section_dir,
        "stem": stem,
    }


def tree(root: Path) -> list[dict]:
    """Walk a dossier root and return a nested module/section/document tree."""
    modules: list[dict] = []
    if not root.exists():
        return modules

    for module_path in sorted(root.iterdir()):
        if not module_path.is_dir():
            continue
        sections: list[dict] = []
        for section_path in sorted(module_path.iterdir()):
            if not section_path.is_dir():
                continue
            section_name = section_path.name
            first_space = section_name.find(" ")
            if first_space > 0:
                spath = section_name[:first_space]
                stitle = section_name[first_space + 1 :]
            else:
                spath = section_name
                stitle = ""

            documents: list[dict] = []
            for item in sorted(section_path.iterdir()):
                if item.suffix == ".json" and item.name.endswith(".meta.json"):
                    continue
                if item.name.endswith(".generated.md") or item.name.endswith(".status.json"):
                    continue
                if item.is_file():
                    meta_file = section_path / f"{item.stem}.meta.json"
                    if meta_file.exists():
                        meta = json.loads(meta_file.read_text())
                    else:
                        meta = {}
                    documents.append(
                        {
                            "name": item.name,
                            "confidence": meta.get("confidence", 0.0),
                            "uploaded_at": meta.get("uploaded_at", ""),
                        }
                    )
            if documents:
                sections.append(
                    {
                        "section_path": spath,
                        "title": stitle,
                        "documents": documents,
                    }
                )
        if sections:
            module_name = module_path.name
            module_meta_file = module_path / ".module.json"
            if module_meta_file.exists():
                module_name = json.loads(module_meta_file.read_text()).get("module", module_name)
            modules.append({"module": module_name, "sections": sections})

    return modules


if __name__ == "__main__":  # self-check: python -m app.services.dossier_service
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        _DOSSIERS_ROOT = Path(tmp)  # module-level rebind for this check only

        a = create_dossier("Povidone Tablet NDA")
        b = create_dossier("Povidone Tablet NDA")  # duplicate name → deduped id
        assert a["id"] == "povidone-tablet-nda"
        assert b["id"] == "povidone-tablet-nda-2"
        assert a["filed"] == 0 and a["approved"] == 0

        ids = {d["id"] for d in list_dossiers()}
        assert ids == {a["id"], b["id"]}

        root_a = dossier_root(a["id"])
        classification = {
            "section_path": "3.2.P.8.1",
            "title": "Stability Summary and Conclusion (Drug Product)",
            "module": "Module 3 — Quality",
            "confidence": 0.85,
        }
        file_into_dossier(root_a, b"payload", "stability.pdf", classification, "extracted text")
        docs_a = list_generated_docs(root_a)
        assert docs_a == []  # filed, but no .generated.md written yet — that's fine, tree() covers filed-only
        t = tree(root_a)
        assert t[0]["sections"][0]["documents"][0]["name"] == "stability.pdf"

        # Dossier B must not see dossier A's document — isolation is the whole point.
        root_b = dossier_root(b["id"])
        assert tree(root_b) == []

        print("OK — multi-dossier isolation, id dedup, and filing verified")
