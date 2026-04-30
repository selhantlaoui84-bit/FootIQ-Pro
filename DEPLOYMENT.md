# FootIQ Pro Deployment

## Backend

Platform: Railway or Render

Build:

```bash
python -m pip install -r requirements.txt
```

Start:

```bash
gunicorn -k uvicorn.workers.UvicornWorker apps.api.main:app -w 2 -b 0.0.0.0:$PORT
```

Environment:

```bash
ENV=production
DEBUG=false
DATABASE_URL=<optional_postgres_url>
REDIS_URL=<optional_redis_url>
CORS_ORIGINS=<frontend_url>
```

Health:

```bash
curl https://<backend_url>/health
```

## Frontend

Platform: Vercel

Root directory:

```bash
apps/web
```

Environment:

```bash
NEXT_PUBLIC_API_URL=<backend_url>
```

Build:

```bash
npm install
npm run build
```

## Test Endpoints

```bash
curl https://<backend_url>/health
curl https://<backend_url>/predictions?match_id=<match_id>
```
