"""Dossier registry: list every dossier and create new ones.

Everything else (upload, plan, chat, ...) is scoped under
/dossiers/{dossier_id}/... — see dossier.py, documents.py, chat.py.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import CreateDossierRequest, DossierSummary
from app.services.dossier_service import create_dossier, get_dossier, list_dossiers

router = APIRouter()


@router.get("", response_model=list[DossierSummary])
def dossiers():
    return list_dossiers()


@router.post("", response_model=DossierSummary)
def create(request: CreateDossierRequest):
    return create_dossier(request.name)


@router.get("/{dossier_id}", response_model=DossierSummary)
def get_one(dossier_id: str):
    summary = get_dossier(dossier_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Dossier not found: {dossier_id}")
    return summary
