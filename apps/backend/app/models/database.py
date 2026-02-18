from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Railway PostgreSQL requires robust pool settings to handle connection drops
# pool_pre_ping: validates connections before use (prevents "connection closed" errors)
# pool_recycle: recycles connections every 5 min (avoids Railway idle timeout drops)
# connect_args: sslmode=require is needed for Railway's managed PostgreSQL
_connect_args = {}
if settings.DATABASE_URL and "railway" in settings.DATABASE_URL:
    _connect_args = {"sslmode": "require"}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

