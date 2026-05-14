import os


def is_email_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") or os.getenv("SENDGRID_API_KEY"))


def send_transactional_email(event_type: str, to_email: str, payload: dict | None = None) -> dict:
    if not is_email_configured():
        return {
            "status": "email_not_configured",
            "sent": False,
            "event_type": event_type,
            "to_email": to_email,
            "detail": "Aucun provider email configuré. Aucun email n'a été envoyé.",
        }
    return {
        "status": "not_implemented",
        "sent": False,
        "event_type": event_type,
        "to_email": to_email,
        "detail": "Provider email détecté, intégration d'envoi à finaliser.",
        "payload_keys": sorted((payload or {}).keys()),
    }
