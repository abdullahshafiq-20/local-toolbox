FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies required by tools (media, OCR, PDF, document conversion, image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    ghostscript \
    pandoc \
    libreoffice-writer \
    unpaper \
    qpdf \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for layer caching
COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install -r requirements.txt

# Copy project files
COPY . .

EXPOSE 18011

CMD ["streamlit", "run", "app.py", "--server.port=18011", "--server.address=0.0.0.0"]
