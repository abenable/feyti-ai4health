"""PostgreSQL-backed CRUD for dossier-scoped ADR reports.

Each report is a FeatureRecord with scope=<dossier id>, kind="pv_report" and
record_key=<report_id>; the full ADRReport payload lives in `data`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List
from uuid import uuid4

from app.models.pv_schemas import ADRReport
from app.services import db_repo

_KIND = "pv_report"


def feature_scope(dossier_id: str) -> str:
    """Validated FeatureRecord scope for a dossier id/root handle."""
    return db_repo.dossier_id_from_root(dossier_id)


def create_report(dossier_id: str, data: Dict) -> ADRReport:
    """Validate, enrich, and persist a new ADR report."""
    report = ADRReport(**data)
    if not report.report_id:
        report.report_id = uuid4().hex
    if not report.worldwide_unique_id:
        report.worldwide_unique_id = f"PM-{report.report_id.upper()}"
    if not report.first_received_date:
        report.first_received_date = date.today()

    db_repo.feature_put(
        feature_scope(dossier_id), _KIND, report.report_id,
        report.model_dump(mode="json"),
    )
    return report


def get_report(dossier_id: str, report_id: str) -> ADRReport | None:
    row = db_repo.feature_get(feature_scope(dossier_id), _KIND, report_id)
    return ADRReport(**row.data) if row is not None else None


def list_reports(dossier_id: str) -> List[ADRReport]:
    reports = [ADRReport(**row.data) for row in db_repo.feature_list(feature_scope(dossier_id), _KIND)]
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

    db_repo.feature_put(feature_scope(dossier_id), _KIND, report_id, updated.model_dump(mode="json"))
    return updated
