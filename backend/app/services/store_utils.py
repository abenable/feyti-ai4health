"""Utility functions for safe JSON file storage.

- ``safe_join`` ensures a relative path does not escape a given root directory.
- ``write_json`` creates parent directories as needed and writes atomically.
- ``read_json`` returns ``None`` for missing files or invalid JSON.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


def safe_join(root: Path | str, rel: Path | str) -> Path:
    """Resolve ``rel`` under ``root`` and assert the result stays within ``root``.

    Raises ``ValueError`` if the resolved path would escape ``root`` (e.g. ``../``
    traversal). Returns the absolute resolved ``Path``.
    """
    root_path = Path(root).resolve()
    target_path = (root_path / rel).resolve()
    # ``target_path`` must be ``root_path`` itself or a descendant.
    if root_path not in target_path.parents and target_path != root_path:
        raise ValueError(f"Path {target_path} escapes root {root_path}")
    return target_path


def write_json(path: Path | str, data: Any) -> None:
    """Write ``data`` as JSON to ``path`` atomically.

    Parent directories are created if missing. The write is performed to a
    temporary ``.tmp`` file in the same directory and then atomically replaced.
    """
    p = Path(path)
    # Ensure parent directories exist.
    if p.parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    # Write to temporary file.
    tmp_path = p.with_name(p.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    # Atomic replace.
    os.replace(tmp_path, p)


def read_json(path: Path | str) -> Optional[Any]:
    """Read JSON from ``path``.

    Returns ``None`` if the file does not exist or contains invalid JSON.
    """
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
