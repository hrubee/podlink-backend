from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

from app.api.v1.endpoints import matches, payments, chat, auth, admin, discovery, users, marketing
from app.models.database import engine, Base
from app.core.config import settings

# Import all models to ensure they are registered with Base before create_all
from app.models.user import User
from app.models.chat import ChatMessage, ChatRoom
from app.models.safety import UserReport, AuditLog
from app.models.matches import Match
from app.models.marketing import WaitlistEntry
from app.models.podcast import Podcast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Sentry ────────────────────────────────────────────────────────────────────
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.2,     # Capture 20% of transactions for performance monitoring
        profiles_sample_rate=0.1,   # Capture 10% for profiling
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
        send_default_pii=False,
    )
    logger.info("✅ Sentry initialized.")
else:
    logger.info("Sentry DSN not set — error monitoring disabled.")

# ── Schema Management ─────────────────────────────────────────────────────────
# On Railway: `alembic upgrade head` runs automatically via the deploy command.
# For local SQLite dev: create_all is still run as a convenience.
if settings.DATABASE_URL.startswith("sqlite"):
    logger.info("SQLite detected — running create_all for local dev convenience.")
    try:
        from app.models.database import engine, Base
        from app.models.matches import Interaction
        Base.metadata.create_all(bind=engine)
        logger.info("✅ SQLite tables ready.")
    except Exception as e:
        logger.error(f"❌ SQLite setup failed: {e}")
        raise
else:
    logger.info("PostgreSQL detected — schema managed by Alembic.")

from app.core.middleware import ObservabilityMiddleware, setup_exception_handlers

app = FastAPI(
    title="PodClip.AI API",
    description="AI-powered podcast host-guest matching platform",
    version="1.0.0",
)

# ── Security Headers Middleware ────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not settings.DATABASE_URL.startswith("sqlite"):
            # Only add HSTS in production (not local dev)
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── Observability Middleware ───────────────────────────────────────────────────
app.add_middleware(ObservabilityMiddleware)
setup_exception_handlers(app)

# ── CORS ─────────────────────────────────────────────────────────────────────
_custom_domain = os.getenv("DOMAIN", "")
_extra_origins = []
if _custom_domain and _custom_domain != "localhost":
    _extra_origins = [f"https://{_custom_domain}", f"http://{_custom_domain}"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://podclip-frontend-production.up.railway.app",
        "https://podclip.radianmedia.org",
        *_extra_origins,
    ],
    allow_origin_regex=r"https://.*\.railway\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/v1",           tags=["Authentication"])
app.include_router(users.router,     prefix="/v1/users",     tags=["Users"])
app.include_router(matches.router,   prefix="/v1/matches",   tags=["Matching"])
app.include_router(payments.router,  prefix="/v1/payments",  tags=["Payments"])
app.include_router(chat.router,      prefix="/v1/chat",      tags=["Chat"])
app.include_router(admin.router,     prefix="/v1/admin",     tags=["Admin"])
app.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
app.include_router(marketing.router, prefix="/v1/marketing", tags=["Marketing"])

from app.api.v1.endpoints import podcast
app.include_router(podcast.router,   prefix="/v1/podcasts",  tags=["Podcasts"])


# ── Health Checks ─────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "PodClip.AI Core Backend",
        "version": "1.0.0",
        "redis": "connected" if settings.REDIS_URL else "disabled",
        "ml_service": settings.ML_SERVICE_URL or "not configured",
        "sentry": "enabled" if settings.SENTRY_DSN else "disabled",
    }


@app.get("/health")
def health_check():
    """Railway health check endpoint."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    """
    Deep health check: verifies the database connection is live.
    Used for monitoring dashboards (not Railway's startup health check —
    that uses the lightweight /health endpoint).
    """
    from sqlalchemy import text
    from app.models.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {"status": "error", "database": str(e)}
