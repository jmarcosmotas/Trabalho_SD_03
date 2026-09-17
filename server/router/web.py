# ---------- Interface web simples para listar e reproduzir os áudios ----------
# Requisito do PDF: "Disponibiliza uma interface web simples para listar os
# áudios armazenados, permitindo sua reprodução diretamente pelo navegador."

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from services.audio_repository import get_all_audios_full

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/")
def homepage(request: Request, db: Session = Depends(get_db)):
    audios = get_all_audios_full(db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"audios": audios},
    )
