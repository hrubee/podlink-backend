from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import redis
import json
import logging
from datetime import datetime, timedelta
from app.services.payments import PaymentService
from app.api import deps, auth_deps
from app.models.user import User
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request Schemas ──────────────────────────────────────────────────────────

# ── Create Checkout Session ──────────────────────────────────────────────────

@router.post("/checkout")
async def create_checkout(
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """Creates a Dodo Payments checkout session for the Pro plan and returns the checkout URL."""
    payment_service = PaymentService(db, r)
    checkout_url = payment_service.create_checkout_session(current_user)
    return {"checkout_url": checkout_url}


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


# ── Dodo Payments Webhook ────────────────────────────────────────────────────

@router.post("/webhook/dodo")
async def dodo_webhook(
    request: Request,
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """
    Handles Dodo Payments webhook events using Standard Webhooks verification.
    Headers used: webhook-id, webhook-signature, webhook-timestamp
    """
    body = await request.body()
    headers = {
        "webhook-id": request.headers.get("webhook-id", ""),
        "webhook-signature": request.headers.get("webhook-signature", ""),
        "webhook-timestamp": request.headers.get("webhook-timestamp", ""),
    }

    payment_service = PaymentService(db, r)

    if not payment_service.verify_webhook(body, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = json.loads(body)
    event_type = data.get("type", "")
    payload = data.get("data", {})

    # Extract user_id from metadata (set during checkout session creation)
    metadata = payload.get("metadata", {})
    user_id = metadata.get("user_id")

    if not user_id:
        logger.warning(f"Dodo webhook missing user_id in metadata: {event_type}")
        return {"status": "ignored", "reason": "no_user_id_in_metadata"}

    logger.info(f"Dodo webhook received: {event_type} for user {user_id}")

    # Subscription lifecycle events
    if event_type in ("subscription.active", "subscription.renewed"):
        # Try to extract the next billing date from the payload
        next_billing = payload.get("next_billing_date")
        if next_billing:
            try:
                ends_at = datetime.fromisoformat(next_billing.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ends_at = None
        else:
            ends_at = None

        await payment_service.activate_paid_status(user_id, plan="pro", ends_at=ends_at)

    elif event_type in (
        "subscription.on_hold",
        "subscription.failed",
        "subscription.cancelled",
        "subscription.expired",
    ):
        await payment_service.deactivate_paid_status(user_id)

    elif event_type == "payment.succeeded":
        logger.info(f"Payment succeeded for user {user_id}")

    elif event_type == "payment.failed":
        logger.warning(f"Payment failed for user {user_id}")

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
