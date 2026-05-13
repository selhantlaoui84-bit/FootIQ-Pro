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
    ("enterprise", "monthly"): "STRIPE_PRICE_ENTERPRISE_MONTHLY",
    ("enterprise", "yearly"): "STRIPE_PRICE_ENTERPRISE_YEARLY",
}
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


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
    price_map = {f"{plan}_{interval}": bool(_env(env_name)) for (plan, interval), env_name in PLAN_PRICE_ENV.items()}
    return {
        "status": "ok",
        "billing_configured": is_billing_configured(),
        "plans": ["free", "pro", "premium", "enterprise"],
        "price_ids_configured": price_map,
        "webhook_configured": bool(_env("STRIPE_WEBHOOK_SECRET")),
        "mode": "live" if _env("STRIPE_SECRET_KEY").startswith("sk_live_") else "test_or_missing",
    }


def _stripe_request(path: str, data: dict, method: str = "POST") -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.stripe.com/v1{path}",
        data=encoded if method.upper() != "GET" else None,
        headers={
            "Authorization": f"Bearer {_env('STRIPE_SECRET_KEY')}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method.upper(),
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _base_success_url(path: str, override: str | None = None) -> str:
    if override:
        return override
    configured = _env(path)
    if configured:
        return configured
    base_url = _env("APP_BASE_URL").rstrip("/")
    if path == "STRIPE_CANCEL_URL":
        return f"{base_url}/billing/cancel"
    if path == "STRIPE_PORTAL_RETURN_URL":
        return f"{base_url}/profile"
    return f"{base_url}/billing/success"


def _get_or_create_customer(user: dict) -> str | None:
    existing = user.get("stripe_customer_id")
    if existing:
        return existing
    response = _stripe_request(
        "/customers",
        {
            "email": user.get("email") or "",
            "name": user.get("display_name") or user.get("email") or "",
            "metadata[user_id]": user.get("id") or "",
            "metadata[user_email]": user.get("email") or "",
            "metadata[source]": "footiq_pro",
        },
    )
    customer_id = response.get("id")
    if customer_id:
        repository.set_user_stripe_customer_id(user.get("id") or user.get("email"), customer_id)
    return customer_id


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


def create_checkout_session_for_user(
    user: dict,
    plan_code: str,
    billing_interval: str = "monthly",
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict:
    if not user or not user.get("id"):
        return {"status": "authentication_required", "detail": "Utilisateur connecté requis."}
    safe_plan = plan_code if plan_code in {"premium", "pro", "enterprise"} else ""
    if not safe_plan:
        return {"status": "invalid_plan", "detail": "Plan inconnu."}
    plan = repository.get_saas_plan_by_code(safe_plan)
    if not plan or not plan.get("is_active"):
        return {"status": "invalid_plan", "detail": "Plan inactif ou indisponible."}
    active = repository.get_active_saas_subscription(user["id"])
    if active and active.get("plan_code") != "free":
        return {"status": "subscription_already_active", "detail": "Un abonnement actif existe déjà.", "subscription": active}
    safe_interval = billing_interval if billing_interval in {"monthly", "yearly"} else "monthly"
    price_id = price_id_for_plan(safe_plan, safe_interval)
    if not is_billing_configured() or not price_id:
        return {"status": "billing_not_configured", "detail": "Paiement non configuré."}

    customer_id = _get_or_create_customer(user)
    if not customer_id:
        return {"status": "stripe_customer_error", "detail": "Impossible de créer le client Stripe."}
    payload = {
        "mode": "subscription",
        "customer": customer_id,
        "client_reference_id": user["id"],
        "success_url": _base_success_url("STRIPE_SUCCESS_URL", success_url),
        "cancel_url": _base_success_url("STRIPE_CANCEL_URL", cancel_url),
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[user_id]": user["id"],
        "metadata[user_email]": user.get("email") or "",
        "metadata[plan_code]": safe_plan,
        "metadata[source]": "footiq_pro",
        "subscription_data[metadata][user_id]": user["id"],
        "subscription_data[metadata][user_email]": user.get("email") or "",
        "subscription_data[metadata][plan_code]": safe_plan,
        "subscription_data[metadata][source]": "footiq_pro",
    }
    session = _stripe_request("/checkout/sessions", payload)
    return {"status": "ok", "checkout_url": session.get("url"), "session_id": session.get("id")}


def create_checkout_session(user_id: str, plan: str, interval: str = "monthly") -> dict:
    user = repository.get_user_by_id_or_email(user_id)
    if not user:
        user = repository.get_or_create_user_by_email(str(user_id), display_name=str(user_id).split("@")[0] if "@" in str(user_id) else None)
    return create_checkout_session_for_user(user, plan, interval)


def create_customer_portal_session_for_user(user: dict) -> dict:
    if not user or not user.get("id"):
        return {"status": "authentication_required", "detail": "Utilisateur connecté requis."}
    if not is_billing_configured():
        return {"status": "billing_not_configured", "detail": "Paiement non configuré."}
    subscription = repository.get_active_saas_subscription(user["id"]) or repository.get_user_subscription(user["id"])
    customer_id = user.get("stripe_customer_id") or subscription.get("provider_customer_id") or subscription.get("stripe_customer_id")
    if not customer_id:
        return {"status": "missing_customer", "detail": "Aucun client Stripe associé à ce compte."}
    session = _stripe_request("/billing_portal/sessions", {"customer": customer_id, "return_url": _base_success_url("STRIPE_PORTAL_RETURN_URL")})
    return {"status": "ok", "portal_url": session.get("url")}


def create_customer_portal_session(user_id: str) -> dict:
    user = repository.get_user_by_id_or_email(user_id)
    return create_customer_portal_session_for_user(user or {"id": user_id})


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


def _object_from_event(event: dict) -> dict:
    return ((event or {}).get("data") or {}).get("object") or {}


def _price_id_from_object(obj: dict) -> str | None:
    lines = (((obj.get("lines") or {}).get("data")) or [])
    if lines:
        return (((lines[0] or {}).get("price") or {}).get("id")) or (((lines[0] or {}).get("plan") or {}).get("id"))
    items = (((obj.get("items") or {}).get("data")) or [])
    if items:
        return ((items[0] or {}).get("price") or {}).get("id")
    return obj.get("stripe_price_id")


def _resolve_user_for_stripe_object(obj: dict) -> dict | None:
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or metadata.get("userid") or obj.get("client_reference_id")
    user_email = metadata.get("user_email") or metadata.get("email")
    customer_id = obj.get("customer")
    user = repository.get_user_by_id_or_email(user_id) or repository.get_user_by_id_or_email(user_email)
    if not user and customer_id:
        user = repository.get_user_by_stripe_customer(str(customer_id))
    if not user and customer_id:
        existing = repository.get_saas_subscription_by_customer(str(customer_id)) or repository.get_subscription_by_customer(str(customer_id))
        user = repository.get_user_by_id_or_email((existing or {}).get("user_id"))
    if not user and user_email:
        user = repository.get_or_create_user_by_email(str(user_email))
    if user and customer_id and not user.get("stripe_customer_id"):
        user = repository.set_user_stripe_customer_id(user["id"], str(customer_id)) or user
    return user


def sync_subscription_from_stripe(event: dict) -> dict:
    event_type = (event or {}).get("type") or "unknown"
    obj = _object_from_event(event)
    metadata = obj.get("metadata") or {}
    metadata_user_id = metadata.get("user_id") or metadata.get("userid") or obj.get("client_reference_id")
    user = _resolve_user_for_stripe_object(obj)

    customer_id = obj.get("customer")
    price_id = _price_id_from_object(obj)
    plan = metadata.get("plan_code") or metadata.get("plan") or map_price_to_plan(price_id)
    status = obj.get("status") or "active"
    subscription_id = obj.get("subscription") if obj.get("object") == "checkout.session" else obj.get("id")
    if obj.get("object") == "invoice":
        subscription_id = obj.get("subscription")
        status = "active" if event_type in {"invoice.paid", "invoice.payment_succeeded"} else ("past_due" if event_type == "invoice.payment_failed" else "pending")
    if obj.get("object") == "payment_intent":
        subscription_id = (metadata or {}).get("subscription_id")
        status = "active" if event_type == "payment_intent.succeeded" else "past_due"
    if event_type == "customer.subscription.deleted":
        status = "canceled"
    if event_type == "checkout.session.completed":
        status = "active"

    if not user and metadata_user_id:
        if event_type == "customer.subscription.deleted":
            plan = "free"
        legacy = repository.upsert_user_subscription(
            user_id=str(metadata_user_id),
            plan=plan,
            status=status,
            stripe_customer_id=str(customer_id) if customer_id else None,
            stripe_subscription_id=str(obj.get("id")) if obj.get("id") else None,
            stripe_price_id=price_id,
            current_period_start=_from_unix(obj.get("current_period_start")),
            current_period_end=_from_unix(obj.get("current_period_end")),
            cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
        )
        return {"status": "ok", "event_type": event_type, "subscription": legacy}
    if not user:
        return {"status": "ignored", "detail": "Webhook sans utilisateur exploitable.", "event_type": event_type}

    if plan == "free" and subscription_id:
        existing = repository.get_saas_subscription_by_provider(str(subscription_id))
        plan = (existing or {}).get("plan_code") or plan

    subscription = None
    if subscription_id or event_type.startswith("customer.subscription") or event_type == "checkout.session.completed":
        subscription = repository.upsert_saas_subscription(
            user["id"],
            plan_code=plan,
            status=status,
            provider="stripe",
            provider_customer_id=str(customer_id) if customer_id else user.get("stripe_customer_id"),
            provider_subscription_id=str(subscription_id) if subscription_id else None,
            current_period_start=_from_unix(obj.get("current_period_start")),
            current_period_end=_from_unix(obj.get("current_period_end")),
            cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
        )
        repository.upsert_user_subscription(
            user_id=user["id"],
            plan=plan if status in ACTIVE_SUBSCRIPTION_STATUSES else "free" if status in {"canceled", "expired", "unpaid"} else plan,
            status=status,
            stripe_customer_id=str(customer_id) if customer_id else user.get("stripe_customer_id"),
            stripe_subscription_id=str(subscription_id) if subscription_id else None,
            stripe_price_id=price_id,
            current_period_start=_from_unix(obj.get("current_period_start")),
            current_period_end=_from_unix(obj.get("current_period_end")),
            cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
        )
        if status in ACTIVE_SUBSCRIPTION_STATUSES:
            repository.sync_entitlements_for_subscription(user["id"], plan, source="plan", actor_email="stripe")
        elif status in {"canceled", "expired", "unpaid"}:
            repository.revoke_plan_entitlements(user["id"], actor_email="stripe")
            repository.sync_entitlements_for_subscription(user["id"], "free", source="plan", actor_email="stripe")

    payment = None
    if event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed", "payment_intent.succeeded", "payment_intent.payment_failed"}:
        paid = event_type in {"invoice.paid", "invoice.payment_succeeded", "payment_intent.succeeded"}
        payment = repository.record_saas_payment(
            user["id"],
            provider_payment_id=obj.get("payment_intent") or obj.get("id"),
            amount_cents=int(obj.get("amount_paid") or obj.get("amount") or obj.get("amount_due") or 0),
            currency=str(obj.get("currency") or "eur").upper(),
            status="succeeded" if paid else "failed",
            subscription_id=(subscription or {}).get("id"),
            provider="stripe",
            paid_at=_from_unix(obj.get("status_transitions", {}).get("paid_at") if isinstance(obj.get("status_transitions"), dict) else obj.get("created")),
            metadata={"stripe_event_type": event_type, "stripe_invoice_id": obj.get("id")},
        )
    repository.write_super_admin_audit("stripe", f"stripe.{event_type}", "stripe_event", (event or {}).get("id"), user.get("email"), None, {"subscription": subscription, "payment": payment})
    return {"status": "ok", "event_type": event_type, "subscription": subscription, "payment": payment}


def handle_stripe_webhook(payload: bytes | dict, signature: str | None = None) -> dict:
    if isinstance(payload, dict):
        event = payload
    else:
        if not _env("STRIPE_WEBHOOK_SECRET"):
            return {"status": "billing_not_configured", "detail": "Webhook Stripe non configuré."}
        if not _verify_signature(payload, signature):
            return {"status": "invalid_signature", "detail": "Signature Stripe invalide."}
        event = json.loads(payload.decode("utf-8"))
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "unknown")
    if event_id:
        previous = repository.stripe_webhook_event_status(event_id)
        if previous and previous.get("status") == "processed":
            return {"status": "ok", "idempotent": True, "event_type": event_type}
    try:
        result = sync_subscription_from_stripe(event)
        if event_id:
            repository.record_stripe_webhook_event(event_id, event_type, "processed", payload=event)
        return result
    except Exception as exc:
        if event_id:
            repository.record_stripe_webhook_event(event_id, event_type, "failed", payload=event, error=str(exc))
        return {"status": "error", "event_type": event_type, "detail": str(exc)}
