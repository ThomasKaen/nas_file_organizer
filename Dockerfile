FROM python:3.13-slim

# Install system deps (Tesseract for OCR + debug tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    sqlite3 \
    curl \
    wget \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .

# Default command: execute once (batch). For a watcher container, swap to nas-watch.
#CMD ["nas-organize", "-c", "/app/rules.yaml", "--execute"]
CMD ["nas-web"]
