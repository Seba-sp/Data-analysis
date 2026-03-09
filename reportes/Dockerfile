FROM python:3.11-slim

# WeasyPrint requires native Pango/HarfBuzz libraries (not pip-installable)
# fonts-noto-color-emoji provides emoji glyph coverage for WeasyPrint PDF output
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Unbuffered output — important for Cloud Run log streaming
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency manifest first — layer cache: pip install only reruns when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (do NOT copy data/ — Cloud Run uses STORAGE_BACKEND=gcs)
COPY core/ ./core/
COPY reports/ ./reports/
COPY templates/ ./templates/
COPY main.py webhook_service.py entrypoint.sh ./

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
