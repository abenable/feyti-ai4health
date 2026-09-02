"""Dossier-scoped pharmacovigilance (ADR reporting) API."""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import require_dossier_root
from app.core.config import settings
from app.models.pv_schemas import ADRReport, MinimumCriteriaCheck, PVReportDraft, PVSourceRequest
from app.services import db_repo, pv_extraction, pv_e2b, pv_meddra, pv_minimum_criteria, pv_service
from app.services.dossier_service import (
    _resolve_section_dir,
    load_extracted_text,
    read_meta,
)

router = APIRouter()


@router.post("/reports", response_model=ADRReport)
def create_report(dossier_id: str, payload: dict):
    return pv_service.create_report(dossier_id, payload)


@router.get("/reports", response_model=List[ADRReport])
def list_reports(dossier_id: str):
    return pv_service.list_reports(dossier_id)


@router.post("/reports/extract", response_model=PVReportDraft)
async def extract_report(dossier_id: str, request: PVSourceRequest, root: Path = Depends(require_dossier_root)):
    try:
        section_dir = _resolve_section_dir(root, request.section_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meta = read_meta(section_dir, request.stem)
    if not meta:
        raise HTTPException(status_code=404, detail="Source document metadata not found")

    extracted_text = load_extracted_text(section_dir, meta)
    if not extracted_text.strip():
        raise HTTPException(status_code=422, detail="Source document has no extracted text")

    return await pv_extraction.extract_report_fields(extracted_text, root)


@router.get("/reports/{report_id}", response_model=ADRReport)
def get_report(dossier_id: str, report_id: str):
    report = pv_service.get_report(dossier_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.put("/reports/{report_id}", response_model=ADRReport)
def update_report(dossier_id: str, report_id: str, updates: dict):
    report = pv_service.update_report(dossier_id, report_id, updates)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports/{report_id}/minimum-criteria", response_model=MinimumCriteriaCheck)
def minimum_criteria(dossier_id: str, report_id: str):
    report = pv_service.get_report(dossier_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    source = report.model_dump(mode="json")
    met = pv_minimum_criteria.criteria_met(source)
    return MinimumCriteriaCheck(
        **met,
        missing=pv_minimum_criteria.missing_criteria(source),
        description=pv_minimum_criteria.describe_missing(source),
    )


@router.post("/meddra/suggest")
async def meddra_suggest(dossier_id: str, term: str):
    return await pv_meddra.suggest(term, dossier_id)


@router.put("/meddra/confirm", response_model=ADRReport)
async def meddra_confirm(dossier_id: str, report_id: str, term: str):
    try:
        return await pv_meddra.confirm(report_id, dossier_id, term)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/follow-ups", response_model=ADRReport)
def add_follow_up(
    dossier_id: str,
    report_id: str,
    date: str,
    description: str | None = None,
):
    report = pv_service.get_report(dossier_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    follow_ups = [item.model_dump(mode="json") for item in report.follow_ups]
    follow_ups.append(
        {"report_id": report_id, "date": date, "description": description}
    )
    updated = pv_service.update_report(dossier_id, report_id, {"follow_ups": follow_ups})
    if updated is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return updated


_EXPECTED_KIND = "pv_expected_reactions"
_EXPECTED_KEY = "expected_reactions"


@router.get("/expected-reactions")
def get_expected(dossier_id: str):
    row = db_repo.feature_get(pv_service.feature_scope(dossier_id), _EXPECTED_KIND, _EXPECTED_KEY)
    return (row.data if row else None) or []


@router.put("/expected-reactions")
def set_expected(dossier_id: str, reactions: List[dict]):
    db_repo.feature_put(pv_service.feature_scope(dossier_id), _EXPECTED_KIND, _EXPECTED_KEY, reactions)
    return {"status": "saved"}


@router.get("/reports/{report_id}/e2b")
def get_e2b(dossier_id: str, report_id: str):
    report = pv_service.get_report(dossier_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        xml = pv_e2b.build_icsr(
            report.model_dump(mode="json"),
            sender_id=settings.PV_SENDER_ID,
            receiver_id=settings.PV_RECEIVER_ID,
        )
    except pv_e2b.E2BValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=xml, media_type="application/xml")
