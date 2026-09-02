"""Pure validation/slug helpers shared by the dossier service and DB repo.

Kept free of any storage imports so both the filesystem-era callers and the
PostgreSQL repo can use them without circular imports.
"""

from __future__ import annotations

import os
import re


def _safe_filename(filename: str) -> str:
    """Return a safe basename; reject path separators and parent references."""
    name = os.path.basename(filename)
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError("Invalid filename")
    return name


def _safe_dir_name(text: str) -> str:
    """Replace storage-hostile characters with underscores."""
    # Keep letters, numbers, spaces, dots, dashes; swap slashes / backslashes.
    return "".join(c if c.isalnum() or c in " .-_" else "_" for c in text).strip()


def _safe_path_part(text: str) -> str:
    """Return a single path component; reject separators and parent refs."""
    if not text or ".." in text or "/" in text or "\\" in text:
        raise ValueError(f"Invalid path component: {text!r}")
    return text


def slugify(name: str) -> str:
    """Turn a display name into a URL-safe id."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "dossier"
