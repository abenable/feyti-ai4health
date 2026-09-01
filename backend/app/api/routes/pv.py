"""Pharmacovigilance (PV) API endpoints.

The routes provide CRUD for ADR reports and expose helper services such as
minimum‑criteria checking, MedDRA suggestion, expected‑reaction handling and E2B
XML generation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import List

from app.models.pv_schemas import ADRReport, MinimumCriteriaCheck
from app.services import pv_service, pv_minimum_criteria, pv_expectedness, pv_meddra, pv_e2b

router = APIRouter()

# ---------------------------------------------------------------------------
# Report CRUD
# ---------------------------------------------------------------------------

@router.post("/reports", response_model=ADRReport)
def create_report(dossier_id: str, payload: dict):
    report = pv_service.create_report(dossier_id, payload)
    return report

@router.get("/reports", response_model=List[ADRReport])
def list_reports(dossier_id: str):
    return pv_service.list_reports(dossier_id)

@router.get("/reports/{report_id}", response_model=ADRReport)
def get_report(dossier_id: str, report_id: str):
    rpt = pv_service.get_report(dossier_id, report_id)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

@router.put("/reports/{report_id}", response_model=ADRReport)
def update_report(dossier_id: str, report_id: str, updates: dict):
    rpt = pv_service.update_report(dossier_id, report_id, updates)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

# ---------------------------------------------------------------------------
# Minimum criteria
# ---------------------------------------------------------------------------

@router.get("/reports/{report_id}/minimum-criteria", response_model=MinimumCriteriaCheck)
def minimum_criteria(dossier_id: str, report_id: str):
    report = pv_service.get_report(dossier_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    met = pv_minimum_criteria.criteria_met(report.model_dump())
    missing = pv_minimum_criteria.missing_criteria(report.model_dump())
    description = pv_minimum_criteria.describe_missing(report.model_dump())
    return MinimumCriteriaCheck(**met, missing=missing, description=description)

# ---------------------------------------------------------------------------
# MedDRA suggestion / confirmation
# ---------------------------------------------------------------------------

@router.post("/meddra/suggest")
def meddra_suggest(dossier_id: str, term: str):
    return pv_meddra.suggest(term, dossier_id)

@router.put("/meddra/confirm")
def meddra_confirm(dossier_id: str, report_id: str, term: str):
    pv_meddra.confirm(report_id, dossier_id, term)
    return {"status": "confirmed"}

# ---------------------------------------------------------------------------
# Follow‑ups (simple append)
# ---------------------------------------------------------------------------

@router.post("/follow-ups")
def add_follow_up(dossier_id: str, report_id: str, date: str, description: str | None = None):
    updates = {"follow_ups": [{"report_id": report_id, "date": date, "description": description}]}
    rpt = pv_service.update_report(dossier_id, report_id, updates)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

# ---------------------------------------------------------------------------
# Expected reactions handling
# ---------------------------------------------------------------------------

@router.get("/expected-reactions")
def get_expected(dossier_id: str):
    from app.services import store_utils
    path = store_utils.safe_join(pv_service._pv_root(dossier_id), "expected_reactions.json")
    data = store_utils.read_json(path)
    return data or []

@router.put("/expected-reactions")
def set_expected(dossier_id: str, reactions: List[dict]):
    from app.services import store_utils
    path = store_utils.safe_join(pv_service._pv_root(dossier_id), "expected_reactions.json")
    store_utils.write_json(path, reactions)
    return {"status": "saved"}

# ---------------------------------------------------------------------------
# E2B XML export
# ---------------------------------------------------------------------------

@router.get("/reports/{report_id}/e2b")
def get_e2b(dossier_id: str, report_id: str):
    report = pv_service.get_report(dossier_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    xml = pv_e2b.build_icsr(report.model_dump(), sender_id="DemoSender", receiver_id="DemoReceiver")
    return Response(content=xml, media_type="application/xml")
