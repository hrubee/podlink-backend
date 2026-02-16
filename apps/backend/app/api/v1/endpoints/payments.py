from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import redis
import json
from app.services.payments import PaymentService
from app.api import deps
from pydantic import BaseModel

router = APIRouter()

class SubscriptionRequest(BaseModel):
    plan_id: str

@router.post("/subscribe")
async def start_subscription(
    request: SubscriptionRequest,
    current_user_id: str = "current_user_id", # Simplified
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    payment_service = PaymentService(db, r)
    try:
        sub = await payment_service.create_subscription(current_user_id, request.plan_id)
        return sub
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    payment_service = PaymentService(db, r)
    body = await request.body()
    
    if not payment_service.verify_webhook(body.decode(), x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_data = json.loads(body)
    event_type = event_data.get("event")
    
    # Logic for subscription events
    if event_type in ["subscription.authenticated", "subscription.activated"]:
        user_id = event_data["payload"]["subscription"]["entity"]["notes"]["user_id"]
        await payment_service.activate_paid_status(user_id)
        
    elif event_type in ["subscription.paused", "subscription.cancelled", "subscription.expired"]:
        user_id = event_data["payload"]["subscription"]["entity"]["notes"]["user_id"]
        await payment_service.deactivate_paid_status(user_id)
        
    return {"status": "processed"}

@router.get("/status")
async def check_status(
    current_user_id: str = "current_user_id",
    r: redis.Redis = Depends(deps.get_redis)
):
    is_paid = r.get(f"user:{current_user_id}:is_paid")
    quota = r.get(f"user:{current_user_id}:quota:outreach") or 0
    
    return {
        "is_premium": is_paid == b"1",
        "current_usage": int(quota),
        "limit": 10
    }
