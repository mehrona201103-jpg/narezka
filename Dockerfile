FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для yt-dlp и ffmpeg (скачивание видео)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём папки для данных
RUN mkdir -p data/movies

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "bot.py"]
