from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Podcast API"
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520 # 8 days
    
    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str
    
    # Podchaser
    PODCHASER_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
