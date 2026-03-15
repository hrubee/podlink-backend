from sqlalchemy.orm import Session
import redis
from datetime import datetime, timedelta
from app.core.config import settings
import hmac
import hashlib

# Plan definitions
PLANS = {
    "pro": {
        "name": "Pro Personality",
        "price_usd_monthly": 19,
        "price_usd_annual": 190,
    },
}

FREE_MONTHLY_LIMIT = 10


class PaymentService:
    def __init__(self, db: Session, r: redis.Redis):
        self.db = db
        self.r = r
        self.free_limit = FREE_MONTHLY_LIMIT
        self.limit_window_days = 30


    def get_usage(self, user_id: str) -> dict:
        """Returns current usage and plan info for the billing dashboard."""
        from app.models.user import User
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return {"plan": "free", "outreach_used": 0, "outreach_limit": FREE_MONTHLY_LIMIT}

        plan = user.subscription_status or "free"
        is_paid = plan == "pro"

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
        if user and user.subscription_status == "pro":
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

    def verify_webhook(self, auth_header: str) -> bool:
        """Verifies RevenueCat webhook via Authorization header."""
        if not settings.REVENUECAT_WEBHOOK_SECRET:
            return True  # Dev mode
        return auth_header == settings.REVENUECAT_WEBHOOK_SECRET

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
