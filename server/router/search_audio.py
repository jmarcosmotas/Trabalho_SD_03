# Esse arquivo e para realizar buscar por audios

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from database.database import get_db
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from services.audio_repository import get_all_audios, get_audio_by_id
from services.get_audio import get_load_audios, get_load_image
from pathlib import Path
from uuid import UUID

router = APIRouter()

# ----------LISTA TODOS OS AUDIOS DO BANCO----------- 
# o usuário envia na URL:
# - audio_id → UUID que identifica o áudio.

# ---------O FAST-API RETORNA UM JSON-----------
# [
#     {
#         "id": "550e8400-e29b-41d4-a716-446655440000",
#         "path_file_original": "storage/2026-09-14/.../original/audio.wav",
#         "path_file_processed": "storage/2026-09-14/.../processed/audio.wav"
#     },
#     {
#         "id": "7c9e6679-7425-40de-944b-e07fc1f90ae",
#         "path_file_original": "storage/2026-09-14/.../original/audio.mp3",
#         "path_file_processed": "storage/2026-09-14/.../processed/audio.mp3"
#     }
# ]

@router.get("/listar-todos-audios")
def list_all_audios(db: Session = Depends(get_db)):
    try:
        audios = get_all_audios(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return audios
    

# ----------O USUARIO VAI BUSCAR AS INFORMAÇOES DE UM AUDIO----------- 
# o usuário envia na URL:
# - audio_id → UUID que identifica o áudio.

# ---------O FAST-API RETORNA UM JSON-----------
# {
#     "original_name": "meu_audio",
#     "original_ext": ".wav",
#     "mime_type": "audio/wav",
#     "size_bytes": 5242880,
#     "duration_sec": 35.42,
#     "sample_rate": 44100,
#     "channels": 2,
#     "bitrate": 1411200,
#     "created_at": "2026-09-14T22:30:15",
#     "processing_type": "normalizacao"
# }

@router.get("/busca-audio/{audio_id}")
def search_audio(audio_id: UUID, db: Session = Depends(get_db)):
    try:
        audio = get_audio_by_id(db, audio_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not audio:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    # AS INFORMAÇOES PRESENTE NO BANCO PRETENCE AO AUDIO ORIGINAL
    return {
        "nome_original": audio.nome_original,
        "extensao": audio.extensao,
        "mime_type": audio.mime_type,
        "size_bytes": audio.size_bytes,
        "duration_sec": audio.duration_sec,
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "bitrate": audio.bitrate,
        "data_time": audio.data_time,
        "processing_type": audio.processing_type
    }

# ----------AQUI E CARREGADO O AUDIO PARA O USUARIO----------
# o usuário envia duas informações na URL:
# audio_id → UUID que identifica o áudio.
# tipo → informa se quer o áudio original ou processed.

# ----------FAST-API RETORNA OS BYTES DO AUDIO PARA REPRODIZIR---------

@router.get("/carregar-audio/{audio_id}/{tipo}")
def load_audio(audio_id: UUID, tipo: str, db: Session = Depends(get_db)):
    try:
        path_audio = get_load_audios(db, audio_id, tipo)
    except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    if not Path(path_audio).exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco")
    
    return FileResponse(
        path=path_audio,
        media_type="application/octet-stream",
        filename=Path(path_audio).name
    )

# ----------CARREGAR IMAGEM DE ONDA----------
# o usuário envia duas informações na URL:
# audio_id → UUID que identifica o áudio.
# tipo → informa se quer o áudio original ou processed.

# ----------FAST-API RETORNA OS BYTES DA IMAGEM PARA RENDERIZAR---------
@router.get("/carregar-imagem/{audio_id}/{tipo}")
def load_image(audio_id: UUID, tipo: str, db: Session = Depends(get_db)):
    try:
        path_image = get_load_image(db, audio_id, tipo)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not Path(path_image).exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada no disco")

    return FileResponse(
        path=path_image,
        media_type="image/png",
        filename=Path(path_image).name
    )
    

    
    