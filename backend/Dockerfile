FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# data dir for the SQLite database (mount a volume here in compose)
ENV DB_PATH=/data/samrudhi.db \
    DATA_DIR=/data \
    OLLAMA_BASE_URL=http://ollama:11434 \
    LLM_PROVIDER=ollama \
    CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173

RUN useradd -m -u 10001 samrudhi && mkdir -p /data && chown -R samrudhi /data /srv
USER samrudhi

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health',timeout=4)" || exit 1

CMD ["sh", "-c", "python scripts/seed.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]