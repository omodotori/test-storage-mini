#models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    original_name = Column(String)
    version = Column(Integer)
    path = Column(String)
    size = Column(Integer)
    uploaded_by = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="file")

class Analysis(Base):
    __tablename__ = "analysis"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"))  # <- Важно!
    result = Column(String)

    file = relationship("File", back_populates="analysis")
