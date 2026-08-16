from fastapi import APIRouter
from app.api.routes import chat, documents, dossier, dossiers

api_router = APIRouter()
api_router.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
api_router.include_router(dossier.router, prefix="/dossiers/{dossier_id}", tags=["dossier"])
api_router.include_router(documents.router, prefix="/dossiers/{dossier_id}/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/dossiers/{dossier_id}/chat", tags=["chat"])
