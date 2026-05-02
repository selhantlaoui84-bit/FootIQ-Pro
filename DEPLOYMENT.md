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
FOOTBALL_DATA_API_KEY=<football_data_org_key_optional>
ADMIN_API_KEY=<admin_refresh_key>
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
NEXT_PUBLIC_SUPABASE_URL=<supabase_project_url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase_anon_key>
NEXT_PUBLIC_ADMIN_API_KEY=<same_value_as_backend_admin_api_key_for_mvp>
```

Build:

```bash
npm install
npm run build
```

## Phase 2 Auth

Supabase Auth handles login, registration, sessions, and logout on the frontend.

Protected frontend routes:

```bash
/dashboard
/admin
/profile
```

Public data routes remain accessible:

```bash
/
/matches
/predictions
/teams
/performance
/about
```

If Supabase env vars are missing, `/login` and `/register` show a setup warning instead of crashing.

Admin refresh is protected by `ADMIN_API_KEY` on Railway and sent from the MVP admin UI through `NEXT_PUBLIC_ADMIN_API_KEY`. If `ENV=production` and `ADMIN_API_KEY` is missing or incorrect, `POST /admin/refresh-data` returns `401`.

## Test Endpoints

```bash
curl https://<backend_url>/health
curl https://<backend_url>/matches
curl https://<backend_url>/predictions
curl -X POST https://<backend_url>/admin/refresh-data -H "X-Admin-Key: <admin_key>"
```
