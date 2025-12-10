FROM python:3.11

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip

# Копируем приложение
COPY app ./app

# Создаем директорию для хранения файлов
RUN mkdir -p ./storage

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]