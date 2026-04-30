# FootIQ Pro Deployment

## Backend

Platform: Railway or Render

Root directory:

```bash
apps/api
```

Build:

```bash
python -m pip install -r requirements.txt
```

Start:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
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
