import razorpay
from sqlalchemy.orm import Session
import redis
from datetime import datetime, timedelta
from app.core.config import settings
import hmac
import hashlib

_RAZORPAY_CONFIGURED = (
    settings.RAZORPAY_KEY_ID not in ("not_configured", "", "your_razorpay_key")
    and settings.RAZORPAY_KEY_SECRET not in ("not_configured", "", "your_razorpay_secret")
)

# Plan definitions — map plan name to Razorpay plan ID
PLANS = {
    "pro": {
        "name": "Pro Personality",
        "price_inr": 2400,   # ₹2400/mo (~$29)
        "razorpay_plan_id": settings.RAZORPAY_PRO_PLAN_ID if hasattr(settings, "RAZORPAY_PRO_PLAN_ID") else "",
    },
    "agency": {
        "name": "Talent Agency",
        "price_inr": 12400,  # ₹12400/mo (~$149)
        "razorpay_plan_id": settings.RAZORPAY_AGENCY_PLAN_ID if hasattr(settings, "RAZORPAY_AGENCY_PLAN_ID") else "",
    },
}

FREE_MONTHLY_LIMIT = 10


class PaymentService:
    def __init__(self, db: Session, r: redis.Redis):
        self.db = db
        self.r = r
        self._razorpay_client = None  # Lazy init — don't crash on startup
        self.free_limit = FREE_MONTHLY_LIMIT
        self.limit_window_days = 30

    @property
    def client(self):
        """Lazily create Razorpay client only when actually needed."""
        if self._razorpay_client is None:
            if not _RAZORPAY_CONFIGURED:
                raise ValueError("Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
            self._razorpay_client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return self._razorpay_client

    async def create_subscription(self, user_id: str, plan: str = "pro"):
        """Creates a Razorpay subscription with a 7-day trial period."""
        if plan not in PLANS:
            raise ValueError(f"Unknown plan: {plan}. Choose from {list(PLANS.keys())}")
        plan_id = PLANS[plan]["razorpay_plan_id"]
        if not plan_id:
            raise ValueError(f"Razorpay plan ID for '{plan}' is not configured.")

        start_at = int((datetime.now() + timedelta(days=7)).timestamp())
        subscription_data = {
            "plan_id": plan_id,
            "customer_notify": 1,
            "total_count": 12,  # Monthly for a year
            "start_at": start_at,
            "notes": {"user_id": user_id, "plan": plan}
        }
        subscription = self.client.subscription.create(data=subscription_data)
        return subscription

    def get_usage(self, user_id: str) -> dict:
        """Returns current usage and plan info for the billing dashboard."""
        from app.models.user import User
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return {"plan": "free", "outreach_used": 0, "outreach_limit": FREE_MONTHLY_LIMIT}

        plan = user.subscription_status or "free"
        is_paid = plan in ("pro", "agency")

        # Count real outreach usage from sliding-window quota in Redis
        outreach_used = 0
        from app.api.deps import NoOpRedis
        if not isinstance(self.r, NoOpRedis):
            quota_key = f"user:{user_id}:quota:outreach:zset"
            now = datetime.now().timestamp()
            window_start = now - (self.limit_window_days * 86400)
            self.r.zremrangebyscore(quota_key, 0, window_start)
            outreach_used = self.r.zcard(quota_key)

        return {
            "plan": plan,
            "is_paid": is_paid,
            "outreach_used": outreach_used,
            "outreach_limit": None if is_paid else FREE_MONTHLY_LIMIT,
            "subscription_ends_at": (
                user.subscription_ends_at.isoformat() if user.subscription_ends_at else None
            ),
        }

    async def check_feature_access(self, user_id: str, feature: str = "outreach") -> bool:
        """
        Feature gating with DB fallback:
        1. Check DB subscription_status (durable even after Redis restart)
        2. Then check Redis sliding-window quota for free users
        """
        from app.models.user import User
        from app.api.deps import NoOpRedis

        # 1. Check DB paid status (durable source of truth)
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if user and user.subscription_status in ("pro", "agency"):
            # Extra guard: check subscription hasn't expired
            if not user.subscription_ends_at or user.subscription_ends_at > datetime.utcnow():
                return True

        # 2. Redis NoOp — allow all in dev when Redis not configured
        if isinstance(self.r, NoOpRedis):
            return True

        # 3. Check Redis fast-path paid flag (cache)
        is_paid = self.r.get(f"user:{user_id}:is_paid")
        if is_paid in (b"1", "1", 1):
            return True

        # 4. Check rolling free quota
        quota_key = f"user:{user_id}:quota:{feature}:zset"
        now = datetime.now().timestamp()
        window_start = now - (self.limit_window_days * 86400)
        self.r.zremrangebyscore(quota_key, 0, window_start)
        current_usage = self.r.zcard(quota_key)

        return current_usage < self.free_limit

    async def increment_quota(self, user_id: str, feature: str = "outreach"):
        """Increments usage for free users using sliding window ZSET."""
        from app.api.deps import NoOpRedis
        if isinstance(self.r, NoOpRedis):
            return

        is_paid = self.r.get(f"user:{user_id}:is_paid")
        if is_paid == b"1":
            return

        quota_key = f"user:{user_id}:quota:{feature}:zset"
        now = datetime.now().timestamp()
        self.r.zadd(quota_key, {str(now): now})
        self.r.expire(quota_key, 2592000)

    def verify_webhook(self, body: str, signature: str) -> bool:
        """Securely verifies Razorpay webhook signature."""
        try:
            self.client.utility.verify_webhook_signature(
                body, signature, settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except Exception:
            return False

    async def activate_paid_status(self, user_id: str, plan: str = "pro", ends_at: datetime = None):
        """Unlocks unlimited access — writes to BOTH Redis (fast) and DB (durable)."""
        from app.models.user import User

        # DB update
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if user:
            user.subscription_status = plan
            user.subscription_ends_at = ends_at or (datetime.utcnow() + timedelta(days=365))
            self.db.commit()

        # Redis cache
        from app.api.deps import NoOpRedis
        if not isinstance(self.r, NoOpRedis):
            self.r.set(f"user:{user_id}:is_paid", "1")

    async def deactivate_paid_status(self, user_id: str):
        """Revokes premium — updates DB and clears Redis cache."""
        from app.models.user import User

        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if user:
            user.subscription_status = "free"
            user.subscription_ends_at = None
            self.db.commit()

        from app.api.deps import NoOpRedis
        if not isinstance(self.r, NoOpRedis):
            self.r.delete(f"user:{user_id}:is_paid")
