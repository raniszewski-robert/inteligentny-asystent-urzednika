# Asystent UDIP (Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej)
# Budowanie:  docker build -t asystent-udip .
# Uruchomienie (offline, reguły + dane demo UMB):
#   docker run --rm -p 8000:8000 -v udip_data:/data asystent-udip
# Z lokalnym modelem Bielik (Ollama na hoście):
#   docker run --rm -p 8000:8000 -v udip_data:/data \
#     --add-host=host.docker.internal:host-gateway \
#     -e LLM_BASE_URL=http://host.docker.internal:11434/v1 asystent-udip

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UDIP_DATA_DIR=/data \
    UDIP_HOST=0.0.0.0 \
    UDIP_PORT=8000 \
    UDIP_APP=app.main:app

# Tesseract OCR >= 5 z językiem polskim (Apache-2.0) – odczyt skanów PDF (udip/ingest.py).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY udip ./udip
COPY scripts ./scripts
COPY data-partner ./data-partner
COPY data-samples ./data-samples
COPY demo_assets ./demo_assets

# Upewnij się, że entrypoint ma końce linii LF (nawet przy budowaniu z Windows) i prawa wykonania.
RUN cp /app/scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin udip \
    && mkdir -p /data \
    && chown -R udip:udip /app /data

USER udip

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"UDIP_PORT\", \"8000\")}/kalendarz', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
