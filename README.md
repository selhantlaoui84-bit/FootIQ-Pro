# FootIQ Pro

FootIQ Pro est une plateforme SaaS d'analyse football pour aider les parieurs à prendre de meilleures décisions via des prédictions probabilistes, un score de confiance, la détection de matchs pièges, l'analyse du risque, le backtesting, le monitoring modèle et un auto-learning progressif.

> ⚠️ **Avertissement important** : FootIQ Pro ne garantit aucun résultat, ne pousse pas au jeu excessif et doit être utilisé comme outil d'aide à la décision uniquement.

## Architecture
- `apps/api` : API FastAPI (prédictions, dashboard, admin, ML ops)
- `apps/web` : Frontend Next.js (dashboard et interfaces utilisateur)
- `docs` : documentation produit/technique
- `scripts` : scripts utilitaires

## Stack technique
- Backend : FastAPI, Uvicorn, SQLAlchemy, PostgreSQL
- Frontend : Next.js, React, TypeScript
- ML : scikit-learn, joblib

## Variables d'environnement
Voir :
- `apps/api/.env.example`
- `apps/web/.env.example`
- `.env.example` (vue globale)

## Lancement local
### Backend
```bash
cd apps/api
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

## Production
- API : `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- Front : `npm run build && npm run start`
- Déploiement : Render (voir `render.yaml`)

## Endpoints principaux
- `GET /health`
- `GET /matches`
- `GET /predictions`
- `GET /dashboard/summary`
- `POST /admin/refresh-data` (protégé par `X-Admin-Key` en production)

## Roadmap courte
- Calibration continue du modèle
- Renforcement du monitoring et de la gouvernance
- Amélioration de l’explicabilité match par match
