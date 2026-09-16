# Esse Arquivo e para processar o audio do enviado 
from pathlib import Path
import subprocess
import datetime
import uuid 
from services.audio_repository import create_audio
import json
import hashlib

def execute_ffmpeg(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise ValueError(result.stderr)
    return result.stdout.strip()

def get_checksum(caminho_arquivo: str) -> str:
    sha256 = hashlib.sha256()

    with open(caminho_arquivo, "rb") as arquivo:
        while bloco := arquivo.read(8192):
            sha256.update(bloco)

    return sha256.hexdigest()

def get_duration(path_file_original):
    command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path_file_original)
        ]
    return float(execute_ffmpeg(command))

def get_sample_rate(path_file_original):
    command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path_file_original)
        ]
    return int(execute_ffmpeg(command))

def get_channels(path_file_original):
    command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=channels",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path_file_original)
        ]
    return int(execute_ffmpeg(command))

def get_bitrate(path_file_original):
    command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path_file_original)
        ]
    return int(execute_ffmpeg(command))


def generate_waveform(path_file_original, path_waveform):
    command = [
        "ffmpeg",
        "-y",
        "-i", str(path_file_original),
        "-filter_complex", "showwavespic=s=1200x300",
        "-frames:v", "1",
        str(path_waveform)
    ]

    execute_ffmpeg(command)



def create_ffmpeg_command(processing_type, path_file_original, path_file_processed, path_json, speed=None, bitrate=None):

    if processing_type == "normalizacao":
        command = [
            "ffmpeg", "-y",
            "-i", str(path_file_original),
            "-af", "loudnorm",
            str(path_file_processed)
        ]
        parameter = {"filtro": "loudnorm"}

    elif processing_type == "mono":
        command = [
            "ffmpeg", "-y",
            "-i", str(path_file_original),
            "-ac", "1",
            str(path_file_processed)
        ]
        parameter = {"channels": 1}

    elif processing_type == "velocidade":
        if speed is None:
            raise ValueError("speed é obrigatório para este processamento")

        if not (0.5 <= speed <= 2.0):
            raise ValueError(
                "O fator de velocidade deve estar entre 0.5 e 2.0"
            )

        command = [
            "ffmpeg", "-y",
            "-i", str(path_file_original),
            "-filter:a", f"atempo={speed}",
            str(path_file_processed)
        ]
        parameter = {"speed": speed}

    elif processing_type == "bitrate":
        if bitrate is None:
            raise ValueError("bitrate é obrigatório para este processamento")

        if not (32 <= bitrate <= 192):
            raise ValueError(
                "bitrate deve estar entre 32k e 192k"
            )

        command = [
            "ffmpeg", "-y",
            "-i", str(path_file_original),
            "-b:a", f"{bitrate}k",
            str(path_file_processed)
        ]
        parameter = {"bitrate_kbps": bitrate}


    elif processing_type == "converter":
        if path_file_original.suffix.lower() == ".mp3":
            path_file_processed = path_file_processed.with_suffix(".wav")
        else:
            path_file_processed = path_file_processed.with_suffix(".mp3")

        command = [
            "ffmpeg", "-y",
            "-i", str(path_file_original),
            str(path_file_processed)
        ]
        parameter = {
            "formato_origem": path_file_original.suffix.lstrip("."),
            "formato_destino": path_file_processed.suffix.lstrip(".")
        }

    else:
        raise ValueError(f"Tipo de processamento inválido: {processing_type}")

    execute = execute_ffmpeg(command)

    size_bytes_original = Path(path_file_original).stat().st_size
    size_bytes_processed = Path(path_file_processed).stat().st_size

    

    meta = {
        "processing_type": processing_type,
        "processing_params": parameter,
        "checksum_original": get_checksum(path_file_original),
        "checksum_processed": get_checksum(path_file_processed),
        "size_bytes_original": size_bytes_original,
        "size_bytes_processed": size_bytes_processed,
    } 

    with open(path_json, "w", encoding="utf-8") as file:
        json.dump(meta, file, indent=4, ensure_ascii=False)

    return path_file_processed, size_bytes_original, execute

async def processor_audio(db, audio, processing_type, speed=None, bitrate=None):
    # Cria um id para o AUDIO
    id_audio = uuid.uuid4()

    # Paga a data atual ANO-MES-DIA
    data_time = datetime.datetime.now()

    # Cria o caminho do arquivo ORIGINAL
    path_original = f"storage/{data_time.date()}/{id_audio}/original"
    storage_original = Path(path_original)
    storage_original.mkdir(parents=True, exist_ok=True)

    # Cria o caminho do arquivo PROCESSADO
    path_processed = f"storage/{data_time.date()}/{id_audio}/processed"
    storage_processed = Path(path_processed)
    storage_processed.mkdir(parents=True, exist_ok=True)

    # A estrutura de ARQUIVO fica:
    # storage/
    #  └── data /                               # Data atual (AAAA-MM-DD)
    #      └── UUID/                            # UUID único gerado para o áudio
    #          ├── original/                    # Pasta para o arquivo original
    #          └── processado/                  # Pasta para o arquivo processado

    # Pega a extensão do arquivo original
    extensao = Path(audio.filename).suffix.lstrip(".")

    # Salva o arquivo com o arquivo original no caminho storage/data/UUID/original/
    path_file_original = f"{path_original}/audio.{extensao}"
    with open(path_file_original, "wb") as file:
        file.write(await audio.read())

    path_file_processed = f"{path_processed}/audio.{extensao}"

    path_json = f"storage/{data_time.date()}/{id_audio}/meta.json"

    # Essa função realiza o processamento no audio
    path_file_processed, size_bytes, message = create_ffmpeg_command(processing_type, path_file_original, path_file_processed, path_json, speed, bitrate)
    print(message)

    # pega o ducação do audio
    duration_sec = get_duration(path_file_original)

    # pega o SAMPLE RATE
    sample_rate = get_sample_rate(path_file_original)

    # pega o CHANEL
    channels = get_channels(path_file_original)

    # pega o BITRATE
    bitrate = get_bitrate(path_file_original)

    # gere a imagem de onda do arquivo original 
    path_waveform_original = f"{path_original}/waveform.png"
    generate_waveform(path_file_original, path_waveform_original)

    # gere a imagem de onda do arquivo processado
    path_waveform_processed = f"{path_processed}/waveform.png"
    generate_waveform(path_file_processed, path_waveform_processed)

    # Criar os metadados no banco de dados
    create_audio(db,
                 id_audio,
                 audio.filename,  
                 extensao, 
                 audio.content_type,
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
                 path_waveform_processed)
    
    # Retorna o caminho do audio PROCESSADO
    return {
        "id_audio": id_audio,
        "processing_type": processing_type
    }


