from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Railway PostgreSQL connection notes:
# - PRIVATE domain (*.railway.internal): NO SSL needed, direct internal connection
# - PUBLIC domain (*.railway.app / proxy): SSL required
# The DATABASE_URL from ${{Postgres.DATABASE_URL}} uses the private domain — no SSL needed.
_connect_args = {}
_db_url = settings.DATABASE_URL or ""

# Only add SSL for public Railway URLs (not internal private domain)
if "railway.app" in _db_url or ("railway" in _db_url and "railway.internal" not in _db_url):
    _connect_args = {"sslmode": "require"}

if _db_url.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,        # Verify connection health before use
        pool_recycle=300,          # Recycle connections after 5 minutes (avoids Railway's idle timeout)
        pool_size=5,               # Maintain 5 persistent connections
        max_overflow=15,           # Allow up to 15 extra connections during bursts
        pool_timeout=10,           # Raise error (not hang) if pool exhausted for > 10s
        pool_reset_on_return="rollback",  # Roll back any uncommitted state on return
        connect_args=_connect_args,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

