from database.database import Base, engine
from database import models

def create_tables():
    Base.metadata.create_all(bind=engine)