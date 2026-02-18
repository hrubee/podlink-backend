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

class PaymentService:
    def __init__(self, db: Session, r: redis.Redis):
        self.db = db
        self.r = r
        self._razorpay_client = None  # Lazy init — don't crash on startup
        self.free_limit = 10
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


    async def create_subscription(self, user_id: str, plan_id: str):
        """Creates a Razorpay subscription with a 7-day trial period."""
        # Calculate trial end (7 days from now)
        start_at = int((datetime.now() + timedelta(days=7)).timestamp())
        
        subscription_data = {
            "plan_id": plan_id,
            "customer_notify": 1,
            "total_count": 12, # Monthly for a year
            "start_at": start_at,
            "notes": {
                "user_id": user_id
            }
        }
        
        subscription = self.client.subscription.create(data=subscription_data)
        return subscription

    async def check_feature_access(self, user_id: str, feature: str = "outreach") -> bool:
        """
        Feature Gating Logic with SLIDING WINDOW:
        1. If Redis is unavailable, allow access (fail open).
        2. If user has 'unlimited' flag in Redis (paid), allow access.
        3. If free, check rolling 30-day quota using Redis ZSET.
        """
        from app.api.deps import NoOpRedis
        if isinstance(self.r, NoOpRedis):
            return True  # Redis not configured — allow all (fail open)

        # 1. Check Paid Status
        is_paid = self.r.get(f"user:{user_id}:is_paid")
        if is_paid in (b"1", "1", 1):
            return True

        # 2. Check Rolling Free Quota (Sliding Window)
        quota_key = f"user:{user_id}:quota:{feature}:zset"
        now = datetime.now().timestamp()
        window_start = now - (self.limit_window_days * 86400)

        # Remove timestamps older than the window
        self.r.zremrangebyscore(quota_key, 0, window_start)

        # Count remaining items in the window
        current_usage = self.r.zcard(quota_key)

        if current_usage >= self.free_limit:
            return False

        return True


    async def increment_quota(self, user_id: str, feature: str = "outreach"):
        """Increments usage for free users using sliding window ZSET."""
        is_paid = self.r.get(f"user:{user_id}:is_paid")
        if is_paid == b"1":
            return
            
        quota_key = f"user:{user_id}:quota:{feature}:zset"
        now = datetime.now().timestamp()
        self.r.zadd(quota_key, {str(now): now})
        # Set expiry for the whole set to 30 days after last use for cleanup
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

    async def activate_paid_status(self, user_id: str):
        """Unlocks unlimited access in Redis."""
        self.r.set(f"user:{user_id}:is_paid", "1")
        # Optional: Set expiry based on subscription end data

    async def deactivate_paid_status(self, user_id: str):
        self.r.delete(f"user:{user_id}:is_paid")
