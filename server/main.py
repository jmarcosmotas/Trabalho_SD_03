from fastapi import FastAPI
from router.receive_audios import receive_audio
from database.init_db import create_tables

create_tables()

app = FastAPI()

app.include_router(receive_audio)