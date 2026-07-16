from fastapi import APIRouter
from app.api.routes import documents, dossier, chat

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(dossier.router, prefix="/dossier", tags=["dossier"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
