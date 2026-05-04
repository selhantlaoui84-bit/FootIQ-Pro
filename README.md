# FootIQ Pro

FootIQ Pro est une plateforme SaaS d’analyse football destinée à aider les parieurs à prendre de meilleures décisions grâce à des prédictions probabilistes, un score de confiance, une analyse du risque, du backtesting et une logique d’auto-learning progressive.

La plateforme ne remplace pas le jugement humain. Elle fournit une aide à la décision basée sur les données, les modèles statistiques et l’historique des performances.

> Avertissement : FootIQ Pro ne garantit aucun résultat sportif ou financier. Le service ne pousse pas au jeu excessif. Les paris comportent un risque de perte d’argent. Utilisez cette plateforme comme un outil d’analyse, pas comme une promesse de gain.

## Objectif du produit

FootIQ Pro vise à devenir un assistant intelligent pour l’analyse de matchs de football. L’objectif est de permettre à l’utilisateur de repérer les opportunités, d’éviter les matchs trop risqués et de comprendre pourquoi une prédiction est considérée comme fiable, prudente ou à éviter.

La plateforme met en avant :

- prédictions 1N2 probabilistes ;
- score de confiance ;
- détection des matchs pièges ;
- score de risque ;
- explications lisibles pour l’utilisateur ;
- suivi des performances ;
- backtesting ;
- monitoring modèle ;
- auto-learning à partir des résultats, erreurs, historiques et comportements utilisateur ;
- assistance intelligente au parieur.

## Architecture

```txt
apps/
  api/    Backend FastAPI
  web/    Frontend Next.js
```

## Stack technique

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- scikit-learn
- football-data.org

### Frontend

- Next.js
- React
- TypeScript
- Supabase, si activé

## Variables d’environnement

### Backend

```env
ENV=production
DATABASE_URL=
FOOTBALL_DATA_API_KEY=
FOOTIQ_COMPETITIONS=FL1,CL,PL,PD,SA,BL1
ADMIN_API_KEY=
CORS_ORIGINS=
```

### Frontend

```env
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## Lancement local du backend

```bash
cd apps/api
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level warning
```

Endpoint de santé :

```bash
http://localhost:8080/health
```

## Lancement local du frontend

```bash
cd apps/web
npm install
npm run dev
```

## Endpoints principaux

```txt
GET  /health
GET  /matches
GET  /matches/{match_id}
GET  /predictions
GET  /predictions/{match_id}
GET  /teams
GET  /teams/{team_id}
GET  /dashboard/summary
GET  /performance
GET  /backtesting
GET  /features/summary
GET  /features/export
GET  /models
GET  /models/governance
GET  /monitoring/model
POST /admin/refresh-data
```

Les routes d’administration doivent être protégées par `ADMIN_API_KEY` en production.

## Déploiement Render

### Backend

Build command :

```bash
cd apps/api && pip install -r requirements.txt
```

Start command :

```bash
cd apps/api && python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level warning
```

Variables recommandées :

```env
ENV=production
DATABASE_URL=<postgresql_url>
FOOTBALL_DATA_API_KEY=<football_data_api_key>
FOOTIQ_COMPETITIONS=FL1,CL,PL,PD,SA,BL1
ADMIN_API_KEY=<strong_admin_key>
CORS_ORIGINS=https://<frontend-domain>
```

### Frontend

Déployer `apps/web` sur Vercel ou Render avec :

```env
NEXT_PUBLIC_API_URL=https://<backend-domain>
```

## Roadmap courte

- Finaliser le nettoyage complet de l’héritage technique inutile.
- Stabiliser le déploiement backend et frontend.
- Connecter PostgreSQL en production.
- Améliorer l’interface dashboard.
- Ajouter un système utilisateur complet.
- Renforcer l’auto-learning et le suivi de performance par utilisateur.
- Ajouter des alertes intelligentes et recommandations personnalisées.

## Licence et responsabilité

FootIQ Pro est un outil d’analyse. L’utilisateur reste responsable de ses décisions. Aucune prédiction ne doit être interprétée comme une certitude.
