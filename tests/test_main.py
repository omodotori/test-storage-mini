import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.main import app, get_db
from app.database import Base
from app.models import File as FileModel, Analysis

# Тестовая база данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_root():
    """Тест корневого эндпоинта"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["version"] == "1.0.0"

def test_upload_file(test_db):
    """Тест загрузки файла"""
    file_content = b"Test file content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    
    response = client.post("/files/upload", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert data["file_name"] == "test.pdf"
    assert data["version"] == 1
    assert data["size"] == len(file_content)
    assert "id" in data

def test_upload_file_versioning(test_db):
    """Тест версионности при повторной загрузке"""
    file_content = b"Test file content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    
    # Первая загрузка
    response1 = client.post("/files/upload", files=files)
    assert response1.json()["version"] == 1
    
    # Вторая загрузка того же файла
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    response2 = client.post("/files/upload", files=files)
    assert response2.json()["version"] == 2
    
    # Третья загрузка
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    response3 = client.post("/files/upload", files=files)
    assert response3.json()["version"] == 3

def test_get_files(test_db):
    """Тест получения списка файлов"""
    # Загружаем тестовый файл
    file_content = b"Test content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    client.post("/files/upload", files=files)
    
    # Получаем список
    response = client.get("/files")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "test.pdf"
    assert data[0]["version"] == 1

def test_analyze_file(test_db):
    """Тест анализа файла"""
    # Загружаем файл
    file_content = b"Test content for analysis"
    files = {"file": ("analysis.pdf", BytesIO(file_content), "application/pdf")}
    upload_response = client.post("/files/upload", files=files)
    file_id = upload_response.json()["id"]
    
    # Анализируем файл
    response = client.post(f"/files/{file_id}/analyze")
    assert response.status_code == 200
    
    data = response.json()
    assert data["file_id"] == file_id
    assert "analysis_id" in data
    assert "result" in data
    assert len(data["result"]) > 0

def test_analyze_nonexistent_file(test_db):
    """Тест анализа несуществующего файла"""
    response = client.post("/files/999/analyze")
    assert response.status_code == 404
    assert "не найден" in response.json()["detail"]

def test_get_analysis(test_db):
    """Тест получения результата анализа"""
    # Загружаем и анализируем файл
    file_content = b"Test content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    upload_response = client.post("/files/upload", files=files)
    file_id = upload_response.json()["id"]
    
    client.post(f"/files/{file_id}/analyze")
    
    # Получаем результат анализа
    response = client.get(f"/files/{file_id}/analysis")
    assert response.status_code == 200
    
    data = response.json()
    assert data["file_id"] == file_id
    assert data["file_name"] == "test.pdf"
    assert "analysis_result" in data

def test_get_analysis_without_running(test_db):
    """Тест получения анализа без его запуска"""
    # Загружаем файл
    file_content = b"Test content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    upload_response = client.post("/files/upload", files=files)
    file_id = upload_response.json()["id"]
    
    # Пытаемся получить анализ без его запуска
    response = client.get(f"/files/{file_id}/analysis")
    assert response.status_code == 404
    assert "не найден" in response.json()["detail"]

def test_get_file_info(test_db):
    """Тест получения информации о файле"""
    # Загружаем файл
    file_content = b"Test content"
    files = {"file": ("info.pdf", BytesIO(file_content), "application/pdf")}
    upload_response = client.post("/files/upload", files=files)
    file_id = upload_response.json()["id"]
    
    # Получаем информацию
    response = client.get(f"/files/{file_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == file_id
    assert data["file_name"] == "info.pdf"
    assert data["version"] == 1
    assert data["size"] == len(file_content)

def test_upload_without_file(test_db):
    """Тест загрузки без файла"""
    response = client.post("/files/upload")
    assert response.status_code == 422  # Validation error