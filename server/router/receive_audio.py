# ---------- Esse arquivo recebe o audio que vai ser processado----------

from fastapi import APIRouter, Depends,  UploadFile, File, Form
from fastapi import HTTPException
from database.database import get_db
from sqlalchemy.orm import Session
from services.audio_processor import processor_audio

router = APIRouter()

# ---------- A REQUISIÇÃO DEVE TER O SEGINTE FORMATO ------------
# curl -X POST http://localhost:8000/ \
#   -F "audio=@musica.mp3" \
#   -F "processing_type=normalizacao" \
#   -F "speed=1.5" \  AQUI COLOCA A VELOCIDADE DO VIDEO O USUARIO VAI DETERMINAR UM VALOR 
#   -F "bitrate=128" O BITRATE O USUARIO TAMBEM VAI ESCOLHER UM VALOR 

# EXEMPLO USANDO O CURL: 
# curl -X POST http://localhost:8080/audios/receber-audio   -F "audio=@arunangshubanerjee-live-football-match-stadium-crowd-cheering-563439.mp3"   -F "processing_type=normalizacao"
#  
# -----------E RETORNADO PARA O CLIENTE O JSON COM O SEGUINTE FORMATO:----------
# {
#     "id": "550e8400-e29b-41d4-a716-446655440000",
#     "processing_type": "normalizacao",
# }

@router.post("/receber-audio")
async def receive_audio_sent(
    audio: UploadFile = File(...),
    processing_type: str = Form(...),
    speed: float | None = Form(None),
    bitrate: int | None = Form(None),
    db: Session = Depends(get_db)
):
    try:
        result = await processor_audio(db, audio, processing_type, speed, bitrate)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "id": result["id_audio"],
        "processing_type": result["processing_type"],
    }




