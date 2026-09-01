from fastapi import APIRouter
from app.api.routes import chat, documents, dossier, dossiers, literature, pv, regintel, translate

api_router = APIRouter()
api_router.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
api_router.include_router(dossier.router, prefix="/dossiers/{dossier_id}", tags=["dossier"])
api_router.include_router(documents.router, prefix="/dossiers/{dossier_id}/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/dossiers/{dossier_id}/chat", tags=["chat"])
api_router.include_router(pv.router, prefix="/dossiers/{dossier_id}/pv", tags=["pv"])
api_router.include_router(translate.router, prefix="/dossiers/{dossier_id}/translate", tags=["translate"])
api_router.include_router(literature.router, prefix="/dossiers/{dossier_id}/literature", tags=["literature"])
api_router.include_router(regintel.router, prefix="/regintelligence", tags=["regintelligence"])
