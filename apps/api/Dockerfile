FROM python:3.11-slim
WORKDIR /app

COPY apps/api/requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY apps/api /app

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
