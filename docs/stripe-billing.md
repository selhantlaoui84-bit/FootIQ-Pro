# Stripe Billing FootIQ Pro

FootIQ Pro utilise Stripe Checkout en mode abonnement. Le client ne crée jamais de session Stripe directement: il appelle `/api/billing/create-checkout-session`, qui transmet le JWT utilisateur au backend.

## Flux

1. Utilisateur connecté choisit Pro, Premium ou Enterprise.
2. Le backend vérifie le plan actif et l'absence d'abonnement déjà actif.
3. Le backend crée ou réutilise le customer Stripe.
4. Checkout est créé en mode `subscription`.
5. Le retour success informe l'utilisateur que l'activation dépend du webhook.
6. Le webhook Stripe synchronise `subscriptions`, `payments` et `access_entitlements`.

## Webhook

Endpoint public Stripe: `/api/webhooks/stripe`.

Le proxy Next transmet le raw body et la signature au backend `/billing/webhook`. Le backend vérifie la signature, journalise `stripe_webhook_events` et traite les événements de façon idempotente.

Événements pris en charge:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `invoice.finalized`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`

Les webhooks sont la source de vérité pour activer ou retirer les droits.
