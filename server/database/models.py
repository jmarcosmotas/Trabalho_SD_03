from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database.database import Base

class Audio(Base):
    __tablename__ = "audio"

    id = Column(UUID(as_uuid=True), primary_key=True)
    original_name = Column(String, nullable=False)
    original_ext = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    duration_sec = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)
    processing_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True))
    path_original = Column(String, nullable=False)
    path_processed = Column(String, nullable=False)
    path_waveform_original = Column(String, nullable=False)
    path_waveform_processed = Column(String, nullable=False)
