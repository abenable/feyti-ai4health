"""Simple filesystem‑backed CRUD for ADR reports.

Each dossier has a ``pv`` subdirectory. Reports are stored as JSON files named
``<report_id>.json``. An ``index.json`` file holds a list of report identifiers
to make enumeration cheap.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Dict

from app.services import store_utils
from app.core.config import settings
from app.models.pv_schemas import ADRReport
from app.services import dossier_service


def _pv_root(dossier_id: str) -> Path:
    root = dossier_service.dossier_root(dossier_id)
    return store_utils.safe_join(root, "pv")


def _ensure_root(dossier_id: str) -> Path:
    pv_root = _pv_root(dossier_id)
    pv_root.mkdir(parents=True, exist_ok=True)
    return pv_root


def _index_path(dossier_id: str) -> Path:
    return _pv_root(dossier_id) / "index.json"


def _load_index(dossier_id: str) -> List[str]:
    data = store_utils.read_json(_index_path(dossier_id))
    return data if isinstance(data, list) else []


def _save_index(dossier_id: str, ids: List[str]) -> None:
    store_utils.write_json(_index_path(dossier_id), ids)


def create_report(dossier_id: str, data: Dict) -> ADRReport:
    """Create a new report and persist it.

    ``data`` is a dict that will be validated against :class:`ADRReport`.
    The function generates a UUID ``report_id`` if one is not supplied.
    """
    pv_root = _ensure_root(dossier_id)
    report = ADRReport(**data)
    if not report.report_id:
        report.report_id = str(uuid.uuid4())
    path = store_utils.safe_join(pv_root, f"{report.report_id}.json")
    store_utils.write_json(path, report.model_dump())
    # update index
    idx = _load_index(dossier_id)
    if report.report_id not in idx:
        idx.append(report.report_id)
        _save_index(dossier_id, idx)
    return report


def get_report(dossier_id: str, report_id: str) -> ADRReport | None:
    path = store_utils.safe_join(_pv_root(dossier_id), f"{report_id}.json")
    data = store_utils.read_json(path)
    return ADRReport(**data) if isinstance(data, dict) else None


def list_reports(dossier_id: str) -> List[ADRReport]:
    ids = _load_index(dossier_id)
    reports = []
    for rid in ids:
        rpt = get_report(dossier_id, rid)
        if rpt:
            reports.append(rpt)
    return reports


def update_report(dossier_id: str, report_id: str, updates: Dict) -> ADRReport | None:
    existing = get_report(dossier_id, report_id)
    if not existing:
        return None
    updated_data = existing.model_dump()
    updated_data.update(updates)
    updated = ADRReport(**updated_data)
    path = store_utils.safe_join(_pv_root(dossier_id), f"{report_id}.json")
    store_utils.write_json(path, updated.model_dump())
    return updated
