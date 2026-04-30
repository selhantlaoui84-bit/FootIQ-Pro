FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY apps ./apps

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker apps.api.main:app -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:${PORT:-8000}"]
