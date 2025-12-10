from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FileResponse(BaseModel):
    id: int
    file_name: str
    version: int
    size: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class FileUploadResponse(BaseModel):
    id: int
    file_name: str
    version: int
    size: int
    uploaded_at: datetime

class FileListItem(BaseModel):
    id: int
    file_name: str
    version: int
    size: int
    uploaded_at: str

class AnalysisResponse(BaseModel):
    file_id: int
    analysis_id: int
    result: str

class AnalysisResultResponse(BaseModel):
    file_id: int
    file_name: str
    version: int
    analysis_result: str