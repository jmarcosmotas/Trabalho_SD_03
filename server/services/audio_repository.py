# Esse arquivo e para operaçoes no banco de dados
from database.models import Audio

def create_audio(
    db,
    id_audio,
    nome_original,
    extensao,
    mime_type,
    size_bytes,
    duration_sec,
    sample_rate,
    channels,
    bitrate,
    data_time,
    processing_type,
    path_file_original,
    path_file_processed,
    path_waveform_original,
    path_waveform_processed
):
        novo_audio = Audio(
            id=id_audio,
            nome_original=nome_original,
            extensao=extensao,
            mime_type=mime_type,
            size_bytes=size_bytes,
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            bitrate=bitrate,
            data_time=data_time,
            processing_type=processing_type,
            path_file_original=path_file_original,
            path_file_processed=path_file_processed,
            path_waveform_original=path_waveform_original,
            path_waveform_processed=path_waveform_processed
        )

        db.add(novo_audio)
        db.commit()


def get_all_audios(db):
    return db.query(Audio.id,
                    Audio.path_file_original,
                    Audio.path_file_processed).order_by(Audio.created_at.desc()).all()

def get_audio_by_id(db, audio_id):
    return db.query(Audio).filter(Audio.id == audio_id).first()

