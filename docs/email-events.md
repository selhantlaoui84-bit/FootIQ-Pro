# Événements email prévus

Aucun email n'est prétendu envoyé si aucun provider n'est configuré.

Variables possibles côté serveur:

- `RESEND_API_KEY`
- `SENDGRID_API_KEY`
- `MAIL_FROM`

Événements à prévoir:

- bienvenue
- paiement réussi
- paiement échoué
- abonnement activé
- abonnement annulé
- trial bientôt terminé
- accès suspendu
- facture disponible
- alerte admin paiement échoué

Sans provider, le service email doit rester no-op avec logs de développement.
