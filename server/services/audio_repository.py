# Esse arquivo e para operaçoes no banco de dados
from database.models import Audio

def create_audio(db, id_audio, nome_original, extensao, mime_type, size_bytes,
                  duration_sec, sample_rate, channels, bitrate, data_time,
                  processing_type, path_file_original, path_file_processed,
                  path_waveform_original, path_waveform_processed):
    try:
        novo_audio = Audio(
            id=id_audio,
            original_name=nome_original,
            original_ext=extensao,
            mime_type=mime_type,
            size_bytes=size_bytes,
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            bitrate=bitrate,
            created_at=data_time,
            processing_type=processing_type,
            path_original=path_file_original,
            path_processed=path_file_processed,
            path_waveform_original=path_waveform_original,
            path_waveform_processed=path_waveform_processed,
        )
        db.add(novo_audio)
        db.commit()
        db.refresh(novo_audio)
        return novo_audio
    except Exception:
        db.rollback()
        raise


def get_all_audios(db):
    return db.query(Audio.id,
                    Audio.path_original,
                    Audio.path_processed).order_by(Audio.created_at.desc()).all()

def get_audio_by_id(db, audio_id):
    return db.query(Audio).filter(Audio.id == audio_id).first()

def get_all_audios_full(db):
    return db.query(Audio).order_by(Audio.created_at.desc()).all()

def delete_audio(db, audio_id):
    try:
        audio = db.query(Audio).filter(Audio.id == audio_id).first()
        if audio:
            db.delete(audio)
            db.commit()
        return audio
    except Exception:
        db.rollback()
        raise

