"""Filesystem-backed dossier placement and tree listing."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_ROOT = Path(settings.DOSSIER_ROOT)


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
        "extracted_chars": len(extracted_text),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    (section_dir / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2))

    return {
        "folder": f"{module}/{section_path} {title}",
        "path": str(file_path),
        "section_path": section_path,
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
