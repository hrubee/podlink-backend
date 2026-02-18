from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PODCHASER_API_KEY: str = ""
    PODCHASER_API_SECRET: str = ""
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    PROJECT_NAME: str = "Ingestion Service"
    ML_SERVICE_URL: str = "http://ml-service:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

