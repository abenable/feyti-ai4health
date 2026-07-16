from fastapi import APIRouter
from app.api.routes import documents, dossier

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(dossier.router, prefix="/dossier", tags=["dossier"])
