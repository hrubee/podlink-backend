from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Podcast API"

    # REQUIRED — fail fast on startup if not set in environment
    SECRET_KEY: str = Field(..., description="JWT signing key. Generate with: openssl rand -hex 32")
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string (postgresql://user:pass@host:5432/db)")

    # Optional — graceful degradation when not present
    REDIS_URL: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours (was 8 days — reduced for security)

    # Razorpay (optional until payments are live)
    RAZORPAY_KEY_ID: str = "not_configured"
    RAZORPAY_KEY_SECRET: str = "not_configured"
    RAZORPAY_WEBHOOK_SECRET: str = "not_configured"
    RAZORPAY_PRO_PLAN_ID: str = ""      # Set in Railway: plan_XXXXXXXXXXXXXXXX
    RAZORPAY_AGENCY_PLAN_ID: str = ""   # Set in Railway: plan_XXXXXXXXXXXXXXXX


    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Observability
    SENTRY_DSN: Optional[str] = None   # Set in Railway: https://xxx@sentry.io/yyy

    # Internal service URLs — MUST be overridden in Railway env vars
    # Default is empty string so it fails loudly instead of silently hitting a Docker hostname
    ML_SERVICE_URL: str = Field(
        default="",
        description="Railway ML service public URL. Set via env var ML_SERVICE_URL."
    )

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore unknown env vars (e.g. Railway injects extras)


settings = Settings()
