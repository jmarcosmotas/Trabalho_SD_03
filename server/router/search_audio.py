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
from services.audio_repository import get_all_audios, get_audio_by_id, delete_audio
from services.audio_processor import move_audio_to_trash  

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

    return [dict(audio._mapping) for audio in audios]

# ----------O USUARIO VAI BUSCAR AS INFORMAÇOES DE UM AUDIO----------- 
# o usuário envia na URL:
# - audio_id → UUID que identifica o áudio.

# EXEMPLO USANDO O CURL: 
# curl http://localhost:8080/audios/busca-audio/fd5f4ab2-d1e4-4ba8-8793-b87dce980f7c4ba8-8793-b87dce980f7c

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

    return {
        "nome_original": audio.original_name,
        "extensao": audio.original_ext,
        "mime_type": audio.mime_type,
        "size_bytes": audio.size_bytes,
        "duration_sec": audio.duration_sec,
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "bitrate": audio.bitrate,
        "data_time": audio.created_at,
        "processing_type": audio.processing_type
    }

# ----------AQUI E CARREGADO O AUDIO PARA O USUARIO----------
# o usuário envia duas informações na URL:
# audio_id → UUID que identifica o áudio.
# tipo → informa se quer o áudio original ou processed.

# EXEMPLO USANDO O CURL:
# curl http://localhost:8080/audios/carregar-audio/e0d21174-869b-4060-ac37-ea885606b4b6/processed --output "/mnt/c/Users/jmarcos/Downloads/audio_processado.mp3"

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

# EXEMPLO USANDO O CURL:
# curl http://localhost:8080/audios/carregar-imagem/e0d21174-869b-4060-ac37-ea885606b4b6/processed --output "/mnt/c/Users/jmarcos/Downloads/waveform_processed.png"

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
    
# ----------EXCLUI UM AUDIO (MOVE PARA A LIXEIRA)----------
# o usuário envia na URL:
# - audio_id → UUID que identifica o áudio.
#
# O áudio não é apagado do disco imediatamente: a pasta inteira
# (original/, processed/, meta.json) é movida para trash/{data}/{uuid}/
# e o registro é removido do banco de dados.
#
# EXEMPLO USANDO O CURL:
# curl -X DELETE http://localhost:8080/audios/deletar-audio/e0d21174-869b-4060-ac37-ea885606b4b6

@router.delete("/deletar-audio/{audio_id}")
def delete_audio_route(audio_id: UUID, db: Session = Depends(get_db)):
    audio = get_audio_by_id(db, audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")

    try:
        move_audio_to_trash(audio)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao mover para a lixeira: {e}")

    delete_audio(db, audio_id)

    return {"detail": "Áudio movido para a lixeira e removido do banco de dados"}
    
    