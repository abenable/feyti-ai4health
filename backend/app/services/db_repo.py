"""Repository helpers mapping the legacy filesystem handles onto PostgreSQL.

The port keeps every service/route signature unchanged: functions still accept
a ``root: Path`` (dossier handle) and a ``section_dir: Path`` (section handle),
but those paths are now opaque keys:

- ``dossier_id``   = ``root.name``
- ``section_path`` = ``"<module_dir>/<section_dir>"`` (folder-relative path)
- a document row is keyed by ``(dossier_id, section_path, stem)``

Handles never need to exist on disk — they are constructed/virtual. All reads
and writes go to the Dossier/Document/FeatureRecord tables in app.db.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import Document, Dossier, FeatureRecord, session_scope
from app.services.dossier_validation import (
    _safe_dir_name,
    _safe_filename,
    _safe_path_part,
    slugify,
)

# ── Handle → key mapping ────────────────────────────────────────────────────


def dossier_id_from_root(root: Path | str) -> str:
    """Extract the validated dossier id from a root handle."""
    return _safe_path_part(Path(root).name)


def section_handle(root: Path | str, module_dir: str, section_dir_name: str) -> Path:
    """Build the virtual section handle (never touches the filesystem)."""
    return Path(root) / module_dir / section_dir_name


def doc_key(section_dir: Path | str, stem: str) -> tuple[str, str, str]:
    """Derive (dossier_id, section_path, stem) from a section handle.

    section_dir is always exactly <dossier_root>/<module_dir>/<section_dir>,
    so the dossier id is two levels up and the section_path is the last two
    components joined — no DOSSIERS_ROOT dependency, works for any root
    (including test tmp dirs).
    """
    d = Path(section_dir)
    dossier_id = _safe_path_part(d.parent.parent.name)
    section_path = f"{_safe_path_part(d.parent.name)}/{_safe_path_part(d.name)}"
    return dossier_id, section_path, _safe_filename(stem)


# ── Dossier CRUD ────────────────────────────────────────────────────────────


def get_dossier_row(dossier_id: str) -> Dossier | None:
    with session_scope() as session:
        return session.get(Dossier, dossier_id)


def ensure_dossier_row(dossier_id: str, name: str | None = None) -> Dossier:
    """Fetch or create the Dossier row (belt for callers that file before create)."""
    with session_scope() as session:
        row = session.get(Dossier, dossier_id)
        if row is None:
            row = Dossier(id=dossier_id, name=name or dossier_id)
            session.add(row)
            session.flush()
        return row


def unique_slug(base_slug: str) -> str:
    """First free dossier id: base_slug, base_slug-2, base_slug-3, ..."""
    with session_scope() as session:
        taken = {
            row for (row,) in session.execute(
                select(Dossier.id).where(Dossier.id.like(f"{base_slug}%"))
            )
        }
    if base_slug not in taken:
        return base_slug
    n = 2
    while f"{base_slug}-{n}" in taken:
        n += 1
    return f"{base_slug}-{n}"


def set_dossier_context(dossier_id: str, context: dict) -> None:
    """Replace a dossier's product context JSON."""
    with session_scope() as session:
        row = session.get(Dossier, dossier_id)
        if row is not None:
            row.context = dict(context)


# ── Document CRUD ───────────────────────────────────────────────────────────


def get_document_row(dossier_id: str, section_path: str, stem: str) -> Document | None:
    with session_scope() as session:
        return session.execute(
            select(Document).where(
                Document.dossier_id == dossier_id,
                Document.section_path == section_path,
                Document.stem == stem,
            )
        ).scalar_one_or_none()


def upsert_document(dossier_id: str, section_path: str, stem: str, **fields: Any) -> Document:
    """Create or replace the document row for (dossier_id, section_path, stem)."""
    with session_scope() as session:
        row = session.execute(
            select(Document).where(
                Document.dossier_id == dossier_id,
                Document.section_path == section_path,
                Document.stem == stem,
            )
        ).scalar_one_or_none()
        if row is None:
            row = Document(dossier_id=dossier_id, section_path=section_path, stem=stem)
            session.add(row)
        for key, value in fields.items():
            setattr(row, key, value)
        session.flush()
        session.refresh(row)
        return row


def list_documents(dossier_id: str) -> list[Document]:
    with session_scope() as session:
        return list(session.execute(
            select(Document)
            .where(Document.dossier_id == dossier_id)
            .order_by(Document.id)
        ).scalars())


def update_document_fields(
    dossier_id: str, section_path: str, stem: str, **fields: Any
) -> Document | None:
    """Partial update; returns None if the row does not exist.

    Pass meta=<dict> to replace the whole JSON meta; pass meta_patch=<dict>
    to merge keys into the existing meta instead. translations_patch=<dict>
    merges {lang: markdown} into the existing translations map.
    """
    meta_patch = fields.pop("meta_patch", None)
    translations_patch = fields.pop("translations_patch", None)
    with session_scope() as session:
        row = session.execute(
            select(Document).where(
                Document.dossier_id == dossier_id,
                Document.section_path == section_path,
                Document.stem == stem,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        if meta_patch:
            meta = dict(row.meta or {})
            meta.update(meta_patch)
            row.meta = meta  # reassign so JSONB change is detected
        if translations_patch:
            translations = dict(row.translations or {})
            translations.update(translations_patch)
            row.translations = translations
        for key, value in fields.items():
            setattr(row, key, value)
        session.flush()
        session.refresh(row)
        return row


# ── FeatureRecord CRUD (regintel / PV / literature) ─────────────────────────


def feature_list(scope: str, kind: str) -> list[FeatureRecord]:
    with session_scope() as session:
        return list(session.execute(
            select(FeatureRecord)
            .where(FeatureRecord.scope == scope, FeatureRecord.kind == kind)
            .order_by(FeatureRecord.id)
        ).scalars())


def feature_get(scope: str, kind: str, record_key: str) -> FeatureRecord | None:
    with session_scope() as session:
        return session.execute(
            select(FeatureRecord).where(
                FeatureRecord.scope == scope,
                FeatureRecord.kind == kind,
                FeatureRecord.record_key == record_key,
            )
        ).scalar_one_or_none()


def feature_put(scope: str, kind: str, record_key: str, data: dict) -> FeatureRecord:
    """Insert or replace one feature record (keeps original created_at on update)."""
    with session_scope() as session:
        row = session.execute(
            select(FeatureRecord).where(
                FeatureRecord.scope == scope,
                FeatureRecord.kind == kind,
                FeatureRecord.record_key == record_key,
            )
        ).scalar_one_or_none()
        if row is None:
            row = FeatureRecord(scope=scope, kind=kind, record_key=record_key, data=data)
            session.add(row)
        else:
            row.data = data
        session.flush()
        session.refresh(row)
        return row


def feature_exists(scope: str, kind: str) -> bool:
    with session_scope() as session:
        return session.execute(
            select(FeatureRecord.id).where(
                FeatureRecord.scope == scope, FeatureRecord.kind == kind
            ).limit(1)
        ).first() is not None
