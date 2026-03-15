from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from app.services.payments import PaymentService
from app.api import deps, auth_deps
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()


# ── Usage / Billing Dashboard ─────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """Returns real usage data for the billing dashboard."""
    payment_service = PaymentService(db, r)
    return payment_service.get_usage(str(current_user.id))


# ── RevenueCat Webhook ────────────────────────────────────────────────────────

@router.post("/webhook/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """
    Handles RevenueCat lifecycle events.
    RevenueCat sends an 'Authorization' header with the webhook secret.
    """
    payment_service = PaymentService(db, r)
    
    if not payment_service.verify_webhook(authorization):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    body = await request.body()
    data = json.loads(body)
    event = data.get("event", {})
    event_type = event.get("type")
    app_user_id = event.get("app_user_id")

    if not app_user_id:
        return {"status": "ignored", "reason": "no_app_user_id"}

    # Map RevenueCat events to app status
    # INITIAL_PURCHASE, RENEWAL -> activate
    # EXPIRATION, REVOCATION -> deactivate
    
    if event_type in ("INITIAL_PURCHASE", "RENEWAL", "SUBSCRIBER_ALIAS"):
        # RevenueCat provides expiration_at_ms
        expiration_ms = event.get("expiration_at_ms")
        ends_at = datetime.utcfromtimestamp(expiration_ms / 1000.0) if expiration_ms else None
        
        # Check if the user has the 'pro' entitlement
        entitlements = event.get("entitlement_ids", [])
        if "pro" in entitlements or not entitlements: # Fallback to true if we just care about any purchase
             await payment_service.activate_paid_status(app_user_id, plan="pro", ends_at=ends_at)

    elif event_type in ("EXPIRATION", "REVOCATION"):
        await payment_service.deactivate_paid_status(app_user_id)

    return {"status": "processed", "event": event_type}


# ── Legacy status check (kept for backwards compat) ───────────────────────────

@router.get("/status")
async def check_status(
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    payment_service = PaymentService(db, r)
    usage = payment_service.get_usage(str(current_user.id))
    return {
        "is_premium": usage["is_paid"],
        "plan": usage["plan"],
        "current_usage": usage["outreach_used"],
        "limit": usage["outreach_limit"],
    }
