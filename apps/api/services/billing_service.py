import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

from data import repository


PLAN_PRICE_ENV = {
    ("premium", "monthly"): "STRIPE_PRICE_PREMIUM_MONTHLY",
    ("premium", "yearly"): "STRIPE_PRICE_PREMIUM_YEARLY",
    ("pro", "monthly"): "STRIPE_PRICE_PRO_MONTHLY",
    ("pro", "yearly"): "STRIPE_PRICE_PRO_YEARLY",
}


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def is_billing_configured() -> bool:
    return bool(_env("STRIPE_SECRET_KEY") and _env("APP_BASE_URL"))


def price_id_for_plan(plan: str, interval: str = "monthly") -> str | None:
    return _env(PLAN_PRICE_ENV.get((plan, interval), "")) or None


def map_price_to_plan(price_id: str | None) -> str:
    if not price_id:
        return "free"
    for (plan, _interval), env_name in PLAN_PRICE_ENV.items():
        if _env(env_name) == price_id:
            return plan
    return "free"


def billing_status() -> dict:
    price_map = {
        "premium_monthly": bool(_env("STRIPE_PRICE_PREMIUM_MONTHLY")),
        "premium_yearly": bool(_env("STRIPE_PRICE_PREMIUM_YEARLY")),
        "pro_monthly": bool(_env("STRIPE_PRICE_PRO_MONTHLY")),
        "pro_yearly": bool(_env("STRIPE_PRICE_PRO_YEARLY")),
    }
    return {
        "status": "ok",
        "billing_configured": is_billing_configured(),
        "plans": ["free", "premium", "pro"],
        "price_ids_configured": price_map,
        "webhook_configured": bool(_env("STRIPE_WEBHOOK_SECRET")),
    }


def _stripe_request(path: str, data: dict) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.stripe.com/v1{path}",
        data=encoded,
        headers={
            "Authorization": f"Bearer {_env('STRIPE_SECRET_KEY')}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def create_checkout_session(user_id: str, plan: str, interval: str = "monthly") -> dict:
    safe_plan = plan if plan in {"premium", "pro"} else "premium"
    safe_interval = interval if interval in {"monthly", "yearly"} else "monthly"
    price_id = price_id_for_plan(safe_plan, safe_interval)
    if not is_billing_configured() or not price_id:
        return {"status": "billing_not_configured", "detail": "Paiement non configuré."}

    base_url = _env("APP_BASE_URL").rstrip("/")
    payload = {
        "mode": "subscription",
        "client_reference_id": user_id,
        "success_url": f"{base_url}/profile?billing=success",
        "cancel_url": f"{base_url}/pricing?billing=cancelled",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[user_id]": user_id,
        "metadata[plan]": safe_plan,
        "subscription_data[metadata][user_id]": user_id,
        "subscription_data[metadata][plan]": safe_plan,
    }
    session = _stripe_request("/checkout/sessions", payload)
    return {"status": "ok", "checkout_url": session.get("url"), "session_id": session.get("id")}


def create_customer_portal_session(user_id: str) -> dict:
    if not is_billing_configured():
        return {"status": "billing_not_configured", "detail": "Paiement non configuré."}
    subscription = repository.get_user_subscription(user_id)
    customer_id = subscription.get("stripe_customer_id")
    if not customer_id:
        return {"status": "missing_customer", "detail": "Aucun client Stripe associé à ce compte."}
    base_url = _env("APP_BASE_URL").rstrip("/")
    session = _stripe_request("/billing_portal/sessions", {"customer": customer_id, "return_url": f"{base_url}/profile"})
    return {"status": "ok", "portal_url": session.get("url")}


def _from_unix(value):
    try:
        return datetime.utcfromtimestamp(int(value)) if value else None
    except Exception:
        return None


def _extract_subscription_object(event: dict) -> dict:
    item = ((event or {}).get("data") or {}).get("object") or {}
    if item.get("object") == "checkout.session":
        subscription_id = item.get("subscription")
        return {
            "id": subscription_id,
            "customer": item.get("customer"),
            "status": "active",
            "metadata": item.get("metadata") or {},
            "items": {"data": []},
        }
    return item


def sync_subscription_from_stripe(event: dict) -> dict:
    event_type = (event or {}).get("type") or "unknown"
    obj = _extract_subscription_object(event)
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or metadata.get("userid") or (obj.get("client_reference_id") if obj.get("object") == "checkout.session" else None)
    customer_id = obj.get("customer")
    if not user_id and customer_id:
        existing = repository.get_subscription_by_customer(str(customer_id))
        user_id = (existing or {}).get("user_id")
    if not user_id:
        return {"status": "ignored", "detail": "Webhook sans user_id exploitable.", "event_type": event_type}

    price_id = None
    items = ((obj.get("items") or {}).get("data") or [])
    if items:
        price_id = ((items[0] or {}).get("price") or {}).get("id")
    price_id = price_id or obj.get("stripe_price_id")
    plan = metadata.get("plan") or map_price_to_plan(price_id)
    status = obj.get("status") or ("canceled" if event_type.endswith(".deleted") else "active")
    if event_type in {"customer.subscription.deleted", "invoice.payment_failed"}:
        status = "canceled" if event_type.endswith(".deleted") else "past_due"
        if event_type.endswith(".deleted"):
            plan = "free"

    subscription = repository.upsert_user_subscription(
        user_id=str(user_id),
        plan=plan,
        status=status,
        stripe_customer_id=str(customer_id) if customer_id else None,
        stripe_subscription_id=str(obj.get("id")) if obj.get("id") else None,
        stripe_price_id=price_id,
        current_period_start=_from_unix(obj.get("current_period_start")),
        current_period_end=_from_unix(obj.get("current_period_end")),
        cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
    )
    return {"status": "ok", "event_type": event_type, "subscription": subscription}


def _verify_signature(payload: bytes, signature: str | None) -> bool:
    secret = _env("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return False
    parts = dict(part.split("=", 1) for part in (signature or "").split(",") if "=" in part)
    timestamp = parts.get("t")
    received = parts.get("v1")
    if not timestamp or not received:
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


def handle_stripe_webhook(payload: bytes | dict, signature: str | None = None) -> dict:
    if isinstance(payload, dict):
        return sync_subscription_from_stripe(payload)
    if not _env("STRIPE_WEBHOOK_SECRET"):
        return {"status": "billing_not_configured", "detail": "Webhook Stripe non configuré."}
    if not _verify_signature(payload, signature):
        return {"status": "invalid_signature", "detail": "Signature Stripe invalide."}
    event = json.loads(payload.decode("utf-8"))
    return sync_subscription_from_stripe(event)
