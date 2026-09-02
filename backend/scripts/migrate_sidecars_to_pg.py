"""One-shot migration of the legacy filesystem stores into PostgreSQL.

Usage (from backend/):
    uv run python scripts/migrate_sidecars_to_pg.py [--dry-run]

Migrates, in order:
  1. dossiers/  — per-dossier dirs (id = dir name): Dossier rows + Document
     rows rebuilt from <stem>.meta.json / .status.json / .generated.md /
     .<lang>.generated.md sidecars and the original uploaded files.
  2. regintel/  — global JSON stores → FeatureRecord(scope="global").
  3. <dossier>/pv/ — ADR reports → FeatureRecord(scope=dossier, kind=pv_report).
  4. <dossier>/literature/ — saved searches → FeatureRecord(literature_search).

Idempotent: every write is an upsert keyed by natural key, so re-running is
safe. --dry-run walks and counts everything without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.services import db_repo  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

LANGUAGES = {"fr", "pt", "sw"}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ! skipping {path.name}: {exc}")
        return None


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def migrate_dossiers(root: Path, dry_run: bool) -> dict:
    counts = {"dossiers": 0, "documents": 0}
    if not root.is_dir():
        return counts
    for dossier_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        meta = _read_json(dossier_dir / ".dossier.json") or {}
        context = _read_json(dossier_dir / ".context.json") or {}
        dossier_id = dossier_dir.name
        counts["dossiers"] += 1
        if not dry_run:
            db_repo.ensure_dossier_row(dossier_id, name=meta.get("name") or dossier_id)
            if isinstance(context, dict) and context:
                db_repo.set_dossier_context(dossier_id, context)

        for meta_path in sorted(dossier_dir.rglob("*.meta.json")):
            meta_doc = _read_json(meta_path)
            if not isinstance(meta_doc, dict):
                continue
            stem = meta_path.name[: -len(".meta.json")]
            section_dir = meta_path.parent
            module_dir = section_dir.parent
            section_path = f"{module_dir.name}/{section_dir.name}"
            meta_doc.setdefault("stem", stem)

            status_doc = _read_json(section_dir / f"{stem}.status.json") or {}
            generated_path = section_dir / f"{stem}.generated.md"
            generated = generated_path.read_text(encoding="utf-8") if generated_path.is_file() else ""

            translations: dict[str, str] = {}
            for candidate in section_dir.glob(f"{stem}.*.generated.md"):
                lang = candidate.name[len(stem) + 1 : -len(".generated.md")]
                if lang in LANGUAGES:
                    translations[lang] = candidate.read_text(encoding="utf-8")

            original_data = None
            filename = meta_doc.get("filename") or ""
            if filename:
                original = section_dir / filename
                if original.is_file():
                    original_data = original.read_bytes()

            fields = dict(
                module=meta_doc.get("module", ""),
                ctd_path=meta_doc.get("section_path", ""),
                title=meta_doc.get("title", ""),
                filename=filename,
                original_data=original_data,
                extracted_text=meta_doc.get("extracted_text", ""),
                pages=meta_doc.get("pages", []),
                meta=meta_doc,
                generated_markdown=generated,
                status=status_doc.get("status", "draft"),
                feedback_history=status_doc.get("feedback_history", []),
                translations=translations,
                uploaded_at=_parse_dt(meta_doc.get("uploaded_at")),
            )
            counts["documents"] += 1
            if not dry_run:
                db_repo.upsert_document(dossier_id, section_path, stem, **fields)
    return counts


def migrate_regintel(root: Path, dry_run: bool) -> dict:
    counts: dict[str, int] = {}
    mapping = {
        "sources.json": ("regintel_source", lambda item: item.get("key", "")),
        "documents.json": ("regintel_document", lambda item: item.get("content_hash", "")),
        "alerts.json": ("regintel_alert", lambda item: item.get("alert_id", "")),
        "changes.json": ("regintel_change", lambda item: uuid.uuid4().hex),
        "deadlines.json": ("regintel_deadline", lambda item: item.get("deadline_id", "")),
    }
    if not root.is_dir():
        return counts
    for filename, (kind, key_fn) in mapping.items():
        items = _read_json(root / filename)
        if not isinstance(items, list):
            continue
        n = 0
        for item in items:
            key = key_fn(item)
            if not key:
                continue
            n += 1
            if not dry_run:
                db_repo.feature_put("global", kind, key, item)
        counts[kind] = n
    return counts


def migrate_dossier_features(root: Path, dry_run: bool) -> dict:
    counts = {"pv_report": 0, "pv_expected_reactions": 0, "pv_meddra_cache": 0, "literature_search": 0}
    if not root.is_dir():
        return counts
    for dossier_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        dossier_id = dossier_dir.name
        pv_dir = dossier_dir / "pv"
        if pv_dir.is_dir():
            for path in sorted(pv_dir.glob("*.json")):
                if path.name == "index.json":
                    continue
                data = _read_json(path)
                if not isinstance(data, dict | list):
                    continue
                if path.name == "expected_reactions.json":
                    if not dry_run:
                        db_repo.feature_put(dossier_id, "pv_expected_reactions", "expected_reactions", data)
                    counts["pv_expected_reactions"] += 1
                    continue
                if path.name == "meddra_cache.json":
                    if not dry_run:
                        db_repo.feature_put(dossier_id, "pv_meddra_cache", "cache", data)
                    counts["pv_meddra_cache"] += 1
                    continue
                if not isinstance(data, dict) or not data.get("report_id"):
                    continue
                counts["pv_report"] += 1
                if not dry_run:
                    db_repo.feature_put(dossier_id, "pv_report", data["report_id"], data)
        lit_dir = dossier_dir / "literature"
        if lit_dir.is_dir():
            for path in sorted(lit_dir.glob("*.json")):
                payload = _read_json(path)
                if not isinstance(payload, dict):
                    continue
                counts["literature_search"] += 1
                if not dry_run:
                    db_repo.feature_put(dossier_id, "literature_search", path.stem, payload)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dossiers-root", default=settings.DOSSIERS_ROOT)
    parser.add_argument("--regintel-root", default=str(REPO_ROOT / "regintel"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        from app.db import init_db

        init_db()
    except Exception as exc:
        print(f"Cannot reach the database ({settings.DATABASE_URL}): {exc}")
        return 1

    print(f"DOSSIERS_ROOT = {args.dossiers_root}")
    print(f"REGINTEL_ROOT = {args.regintel_root}")
    if args.dry_run:
        print("DRY RUN — no writes will be performed\n")

    dossiers = migrate_dossiers(Path(args.dossiers_root), args.dry_run)
    regintel = migrate_regintel(Path(args.regintel_root), args.dry_run)
    features = migrate_dossier_features(Path(args.dossiers_root), args.dry_run)

    print(f"\ndossiers:            {dossiers['dossiers']}")
    print(f"documents:           {dossiers['documents']}")
    for kind, n in regintel.items():
        print(f"regintel/{kind}:   {n}")
    for kind, n in features.items():
        print(f"{kind}:   {n}")
    print(args.dry_run and "Dry run complete." or "Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
