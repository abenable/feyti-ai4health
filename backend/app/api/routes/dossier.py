from fastapi import APIRouter
from app.models.schemas import DossierModule
from app.services.dossier_service import tree

router = APIRouter()


@router.get("/tree", response_model=list[DossierModule])
def dossier_tree():
    return tree()
