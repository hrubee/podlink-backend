from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Podcast API"
    SECRET_KEY: str = "changeme-generate-with-openssl-rand-hex-32"
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None  # Optional: graceful degradation if not set
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520  # 8 days

    # Razorpay (optional until payments are live)
    RAZORPAY_KEY_ID: str = "not_configured"
    RAZORPAY_KEY_SECRET: str = "not_configured"
    RAZORPAY_WEBHOOK_SECRET: str = "not_configured"
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Internal service URLs — override these in Railway env vars
    # In Docker Compose they use service names; in Railway use the public URLs
    ML_SERVICE_URL: str = "http://ml-service:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore unknown env vars (e.g. Railway injects extras)

settings = Settings()

