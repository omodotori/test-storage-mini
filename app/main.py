from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import logging
from datetime import datetime
from typing import List

from .database import SessionLocal, init_db
from .models import File as FileModel, Analysis
from .schemas import FileUploadResponse, FileListItem, AnalysisResponse, AnalysisResultResponse, FileResponse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Storage Service",
    description="Сервис для хранения документов с версионностью и AI-анализом",
    version="1.0.0"
)

init_db()

STORAGE_DIR = "./storage"
os.makedirs(STORAGE_DIR, exist_ok=True)
logger.info(f"Storage directory initialized at {STORAGE_DIR}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mock AI анализ функция (вместо OpenAI)
def mock_ai_analysis(file_name: str, file_size: int, version: int) -> str:
    """Имитация AI анализа без использования внешних API"""
    logger.info(f"Running AI analysis for {file_name} (v{version}, {file_size} bytes)")
    
    if file_size < 10000:
        return f"Файл '{file_name}' очень маленький ({file_size} байт), версия {version}. Изменения минимальны."
    elif file_size < 100000:
        return f"Файл '{file_name}' относительно небольшой ({file_size} байт), новое изменение выглядит незначительным."
    elif file_size < 1000000:
        return f"Файл '{file_name}' среднего размера ({file_size} байт), версия {version}. Возможны существенные изменения."
    else:
        return f"Файл '{file_name}' большой ({file_size} байт), версия {version}. Документ содержит значительный объем данных."

@app.get("/")
def root():
    """Корневой эндпоинт"""
    return {
        "message": "Document Storage API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "POST /files/upload",
            "list": "GET /files",
            "analyze": "POST /files/{file_id}/analyze",
            "get_analysis": "GET /files/{file_id}/analysis"
        }
    }

@app.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Загрузка файла с автоматической версионностью"""
    if not file.filename:
        logger.warning("Upload attempt with no filename")
        raise HTTPException(status_code=400, detail="Файл не выбран")

    logger.info(f"Uploading file: {file.filename}")

    # Проверяем существующие версии файла
    existing = db.query(FileModel).filter(
        FileModel.original_name == file.filename
    ).order_by(FileModel.version.desc()).first()
    
    version = existing.version + 1 if existing else 1
    logger.info(f"File version: {version}")

    # Сохраняем файл с версией в имени
    filename_on_disk = f"{file.filename}_v{version}"
    filepath = os.path.join(STORAGE_DIR, filename_on_disk)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    
    logger.info(f"File saved to {filepath}, size: {len(contents)} bytes")

    # Записываем в БД
    file_db = FileModel(
        original_name=file.filename,
        version=version,
        path=filepath,
        size=len(contents),
        uploaded_by=1
    )
    db.add(file_db)
    db.commit()
    db.refresh(file_db)

    logger.info(f"File record created in DB with ID: {file_db.id}")

    return FileUploadResponse(
        id=file_db.id,
        file_name=file.filename,
        version=version,
        size=len(contents),
        uploaded_at=file_db.uploaded_at
    )

@app.get("/files", response_model=List[FileListItem])
def get_files(db: Session = Depends(get_db)):
    """Получение списка всех файлов"""
    logger.info("Fetching all files")
    files = db.query(FileModel).order_by(FileModel.uploaded_at.desc()).all()
    
    logger.info(f"Found {len(files)} files")
    
    return [
        FileListItem(
            id=f.id,
            file_name=f.original_name,
            version=f.version,
            size=f.size,
            uploaded_at=f.uploaded_at.isoformat()
        )
        for f in files
    ]

@app.post("/files/{file_id}/analyze", response_model=AnalysisResponse)
def analyze_file(file_id: int, db: Session = Depends(get_db)):
    """Запуск AI анализа файла"""
    logger.info(f"Analyzing file with ID: {file_id}")
    
    file_db = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_db:
        logger.warning(f"File not found: {file_id}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Проверяем, есть ли уже анализ
    existing_analysis = db.query(Analysis).filter(Analysis.file_id == file_id).first()
    
    # Выполняем mock AI анализ
    analysis_result = mock_ai_analysis(
        file_name=file_db.original_name,
        file_size=file_db.size,
        version=file_db.version
    )
    
    if existing_analysis:
        # Обновляем существующий анализ
        logger.info(f"Updating existing analysis: {existing_analysis.id}")
        existing_analysis.result = analysis_result
        db.commit()
        analysis_id = existing_analysis.id
    else:
        # Создаем новый анализ
        logger.info("Creating new analysis record")
        analysis = Analysis(
            file_id=file_id,
            result=analysis_result
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        analysis_id = analysis.id
    
    logger.info(f"Analysis completed with ID: {analysis_id}")
    
    return AnalysisResponse(
        file_id=file_id,
        analysis_id=analysis_id,
        result=analysis_result
    )

@app.get("/files/{file_id}/analysis", response_model=AnalysisResultResponse)
def get_analysis(file_id: int, db: Session = Depends(get_db)):
    """Получение результата анализа файла"""
    logger.info(f"Fetching analysis for file ID: {file_id}")
    
    file_db = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_db:
        logger.warning(f"File not found: {file_id}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    analysis = db.query(Analysis).filter(Analysis.file_id == file_id).first()
    
    if not analysis:
        logger.warning(f"Analysis not found for file: {file_id}")
        raise HTTPException(
            status_code=404,
            detail="Анализ не найден. Сначала запустите POST /files/{file_id}/analyze"
        )
    
    logger.info(f"Analysis found: {analysis.id}")
    
    return AnalysisResultResponse(
        file_id=file_id,
        file_name=file_db.original_name,
        version=file_db.version,
        analysis_result=analysis.result
    )

@app.get("/files/{file_id}", response_model=FileResponse)
def get_file_info(file_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном файле"""
    logger.info(f"Fetching file info for ID: {file_id}")
    
    file_db = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not file_db:
        logger.warning(f"File not found: {file_id}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        id=file_db.id,
        file_name=file_db.original_name,
        version=file_db.version,
        size=file_db.size,
        uploaded_at=file_db.uploaded_at
    )