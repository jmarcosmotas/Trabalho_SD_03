from services.audio_repository import get_audio_paths_by_id

def get_load_audios(db, audio_id, tipo):
    audio = get_audio_paths_by_id(db, audio_id)
    if not audio:
        raise ValueError("Áudio não encontrado")

    if tipo == "original":
        path_audio = audio.path_original
    elif tipo == "processed":
        path_audio = audio.path_processed
    else:
        raise ValueError("tipo deve ser 'original' ou 'processed'")

    return path_audio

  
def get_load_image(db, audio_id, tipo):
    audio = get_audio_paths_by_id(db, audio_id)
    if not audio:
        raise ValueError("Áudio não encontrado")

    if tipo == "original":
        path_image = audio.path_waveform_original
    elif tipo == "processed":
        path_image = audio.path_waveform_processed
    else:
        raise ValueError("tipo deve ser 'original' ou 'processed'")
    
    return path_image