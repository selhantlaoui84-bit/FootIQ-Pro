# FootIQ Pro - Variables de production

Toutes les variables sensibles doivent rester côté serveur.

## Railway backend

- `DATABASE_URL`: PostgreSQL de production.
- `ADMIN_API_KEY`: clé serveur pour les opérations admin.
- `APP_BASE_URL`: URL publique de l'app web.
- `SUPABASE_URL` et `SUPABASE_ANON_KEY`: validation du JWT utilisateur côté backend.
- `ODDS_PROVIDER`, `ODDS_API_KEY`, `ODDS_BASE_URL`, `ODDS_REGION`, `ODDS_MARKETS`, `ODDS_BOOKMAKERS`: cotes réelles.
- `STRIPE_SECRET_KEY`: clé secrète Stripe test ou live.
- `STRIPE_WEBHOOK_SECRET`: secret du webhook Stripe.
- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`, `STRIPE_PORTAL_RETURN_URL`: retours Checkout/Portal.
- `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_YEARLY`.
- `STRIPE_PRICE_PREMIUM_MONTHLY`, `STRIPE_PRICE_PREMIUM_YEARLY`.
- `STRIPE_PRICE_ENTERPRISE_MONTHLY`, `STRIPE_PRICE_ENTERPRISE_YEARLY`.

## Vercel web

- `NEXT_PUBLIC_API_URL`: URL du backend Railway.
- `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY`: auth client Supabase.
- `ADMIN_API_KEY`: uniquement dans les variables serveur Vercel pour les proxies admin.

Ne jamais créer de variable publique pour les clés admin, odds ou Stripe secrètes.

## Test vs live

En mode test, utiliser les clés `sk_test_...` et les price IDs de test. En live, basculer ensemble la clé secrète, les price IDs, les webhooks et les produits Stripe. Ne jamais mélanger price IDs test et clé live.

## Checklist avant live

- Webhook Stripe live configuré vers `/api/webhooks/stripe`.
- Produits et prix Stripe créés pour Pro, Premium et Enterprise.
- `samir.elh@outlook.fr` confirmé `super_admin`.
- `/system/production-health` sans erreur.
- Cotes réelles configurées ou fallback “Cote réelle non disponible”.
- Tests et build validés.
