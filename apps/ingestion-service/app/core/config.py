from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PODCHASER_API_KEY: str
    PODCHASER_API_SECRET: str
    DATABASE_URL: str
    REDIS_URL: str
    PROJECT_NAME: str = "Ingestion Service"
    
    class Config:
        env_file = ".env"

settings = Settings()
