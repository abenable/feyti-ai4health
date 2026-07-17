"""Filesystem-backed dossier placement and tree listing."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_ROOT = Path(settings.DOSSIER_ROOT)

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


def _resolve_section_dir(path_param: str) -> Path:
    """Convert a slash-separated dossier path into a verified Path under _ROOT.

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
    section_dir = (_ROOT / module_part / section_part).resolve()
    root = _ROOT.resolve()
    if root not in section_dir.parents and section_dir != root:
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


def resolve_document_paths(path_param: str, stem: str) -> dict:
    """Resolve section_path + stem to verified file paths under DOSSIER_ROOT.

    Returns {"section_dir": Path, "generated": Path, "status": Path, "meta": Path}.
    Raises ValueError for traversal attempts or paths outside the dossier.
    """
    section_dir = _resolve_section_dir(path_param)
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


def list_generated_docs() -> list[dict]:
    """Return every generated document + status across the dossier."""
    docs: list[dict] = []
    if not _ROOT.exists():
        return docs
    for generated in sorted(_ROOT.rglob("*.generated.md")):
        section_dir = generated.parent
        stem = generated.stem.replace(".generated", "")
        status = _read_status(section_dir, stem)
        meta = read_meta(section_dir, stem)
        rel = section_dir.relative_to(_ROOT)
        docs.append(
            {
                "section_path": str(rel),
                "stem": stem,
                "filename": meta.get("filename", ""),
                "title": meta.get("title", ""),
                "module": meta.get("module", ""),
                "status": status["status"],
                "updated_at": status["updated_at"],
                "feedback_count": len(status.get("feedback_history", [])),
            }
        )
    return docs


def file_into_dossier(file_bytes, filename, classification, extracted_text) -> dict:
    """Write file and metadata under DOSSIER_ROOT/<module>/<section>."""
    name = _safe_filename(filename)
    stem = Path(name).stem

    module = classification["module"]
    section_path = classification["section_path"]
    title = classification["title"]

    module_dir = _ROOT / _safe_dir_name(module)
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
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    (section_dir / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2))

    return {
        "folder": f"{module}/{section_path} {title}",
        "path": str(file_path),
        "section_path": section_path,
        "section_dir": section_dir,
        "stem": stem,
    }


def tree() -> list[dict]:
    """Walk DOSSIER_ROOT and return a nested module/section/document tree."""
    modules: list[dict] = []
    if not _ROOT.exists():
        return modules

    for module_path in sorted(_ROOT.iterdir()):
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
