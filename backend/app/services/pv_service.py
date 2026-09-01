"""Filesystem-backed CRUD for dossier-scoped ADR reports."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from app.models.pv_schemas import ADRReport
from app.services import dossier_service, store_utils


def _pv_root(dossier_id: str) -> Path:
    root = dossier_service.dossier_root(dossier_id)
    return store_utils.safe_join(root, "pv")


def _ensure_root(dossier_id: str) -> Path:
    pv_root = _pv_root(dossier_id)
    pv_root.mkdir(parents=True, exist_ok=True)
    return pv_root


def _index_path(dossier_id: str) -> Path:
    return store_utils.safe_join(_pv_root(dossier_id), "index.json")


def _load_index(dossier_id: str) -> List[str]:
    data = store_utils.read_json(_index_path(dossier_id))
    return data if isinstance(data, list) else []


def _save_index(dossier_id: str, ids: List[str]) -> None:
    store_utils.write_json(_index_path(dossier_id), ids)


def create_report(dossier_id: str, data: Dict) -> ADRReport:
    """Validate, enrich, and persist a new ADR report."""
    _ensure_root(dossier_id)
    report = ADRReport(**data)
    if not report.report_id:
        report.report_id = uuid4().hex
    if not report.worldwide_unique_id:
        report.worldwide_unique_id = f"PM-{report.report_id.upper()}"
    if not report.first_received_date:
        report.first_received_date = date.today()

    path = store_utils.safe_join(_pv_root(dossier_id), f"{report.report_id}.json")
    store_utils.write_json(path, report.model_dump(mode="json"))

    index = _load_index(dossier_id)
    if report.report_id not in index:
        index.append(report.report_id)
        _save_index(dossier_id, index)
    return report


def get_report(dossier_id: str, report_id: str) -> ADRReport | None:
    path = store_utils.safe_join(_pv_root(dossier_id), f"{report_id}.json")
    data = store_utils.read_json(path)
    return ADRReport(**data) if isinstance(data, dict) else None


def list_reports(dossier_id: str) -> List[ADRReport]:
    reports = [report for report_id in _load_index(dossier_id)
               if (report := get_report(dossier_id, report_id)) is not None]
    return sorted(reports, key=lambda report: report.created_at, reverse=True)


def update_report(dossier_id: str, report_id: str, updates: Dict) -> ADRReport | None:
    existing = get_report(dossier_id, report_id)
    if existing is None:
        return None

    updated_data = existing.model_dump(mode="json")
    updated_data.update(updates)
    updated = ADRReport(**updated_data)
    updated.updated_at = datetime.utcnow()
    updated.report_id = report_id

    path = store_utils.safe_join(_pv_root(dossier_id), f"{report_id}.json")
    store_utils.write_json(path, updated.model_dump(mode="json"))
    return updated
