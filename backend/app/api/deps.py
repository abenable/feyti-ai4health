"""Shared FastAPI dependencies for dossier-scoped routes."""

from pathlib import Path

from fastapi import HTTPException

from app.services.dossier_service import dossier_root, get_dossier


def require_dossier_root(dossier_id: str) -> Path:
    """Resolve dossier_id to its root Path, or 404 if the dossier doesn't exist."""
    if get_dossier(dossier_id) is None:
        raise HTTPException(status_code=404, detail=f"Dossier not found: {dossier_id}")
    return dossier_root(dossier_id)
