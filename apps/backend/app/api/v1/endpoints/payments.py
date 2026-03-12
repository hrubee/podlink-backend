from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from app.services.payments import PaymentService, _RAZORPAY_CONFIGURED
from app.api import deps, auth_deps
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()


class SubscriptionRequest(BaseModel):
    plan: str = "pro"   # "pro"
    billing_cycle: str = "monthly"  # "monthly" | "annual"


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


# ── Create Subscription ───────────────────────────────────────────────────────

@router.post("/subscribe")
async def start_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """Initiates a Razorpay subscription with a 7-day free trial."""
    if not _RAZORPAY_CONFIGURED:
        raise HTTPException(status_code=503, detail="Payment system not configured yet.")
    payment_service = PaymentService(db, r)
    try:
        sub = await payment_service.create_subscription(str(current_user.id), request.plan, request.billing_cycle)
        return sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Razorpay Webhook ──────────────────────────────────────────────────────────

@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    """
    Handles Razorpay subscription lifecycle events.
    Events handled:
      - subscription.activated / subscription.charged  → activate premium
      - subscription.paused / subscription.cancelled / subscription.expired → deactivate
      - payment.failed → log, no immediate action (Razorpay retries automatically)
    """
    if not _RAZORPAY_CONFIGURED:
        raise HTTPException(status_code=503, detail="Payment system not configured.")

    payment_service = PaymentService(db, r)
    body = await request.body()

    if not x_razorpay_signature or not payment_service.verify_webhook(body.decode(), x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_data = json.loads(body)
    event_type = event_data.get("event")

    try:
        subscription_entity = event_data["payload"]["subscription"]["entity"]
        user_id = subscription_entity["notes"]["user_id"]
        plan = subscription_entity["notes"].get("plan", "pro")
    except (KeyError, TypeError):
        # Some events (e.g. payment.failed) may not have subscription payload
        return {"status": "skipped", "event": event_type}

    if event_type in ("subscription.activated", "subscription.charged"):
        # Work out when the current subscription period ends
        current_end = subscription_entity.get("current_end")
        ends_at = datetime.utcfromtimestamp(current_end) if current_end else None
        await payment_service.activate_paid_status(user_id, plan=plan, ends_at=ends_at)

    elif event_type in ("subscription.paused", "subscription.cancelled", "subscription.expired"):
        await payment_service.deactivate_paid_status(user_id)

    elif event_type == "payment.failed":
        # Log the failure — Razorpay will retry; no immediate action needed
        import logging
        logging.getLogger(__name__).warning(
            f"Razorpay payment.failed for user {user_id}: {event_data}"
        )

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
