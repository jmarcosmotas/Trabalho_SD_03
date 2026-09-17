from fastapi import FastAPI
from database.init_db import create_tables
from router.receive_audio import router as receive_audio_sent
from router.search_audio import router as search_audios
from router.web import router as web_interface




create_tables()

app = FastAPI()


app.include_router(receive_audio_sent, prefix="/audios", tags=["Upload"])
app.include_router(search_audios, prefix="/audios", tags=["Áudios"])
app.include_router(web_interface, tags=["Interface Web"])
