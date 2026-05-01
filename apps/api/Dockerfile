FROM python:3.11-slim
WORKDIR /app

COPY apps/api/requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY apps/api /app

CMD ["sh", "-c", "gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}"]
