from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.api.v1.endpoints import matches, payments, chat, auth, admin, agency, discovery, users, marketing
from app.models.database import engine, Base
from app.core.config import settings

# Import all models to ensure they are registered with Base before create_all
from app.models.user import User
from app.models.chat import ChatMessage, ChatRoom
from app.models.safety import UserReport, AuditLog
from app.models.matches import Match
from app.models.agency import Agency
from app.models.marketing import WaitlistEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auto-create all tables on startup (idempotent — safe to run on every deploy)
logger.info("Running database migrations (create_all)...")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready.")
except Exception as e:
    logger.error(f"❌ Database setup failed: {e}")
    raise  # Fail fast — don't start if DB is broken

from app.core.middleware import ObservabilityMiddleware, setup_exception_handlers

app = FastAPI(
    title="PodMatch.AI API",
    description="AI-powered podcast host-guest matching platform",
    version="1.0.0",
)

# Observability middleware
app.add_middleware(ObservabilityMiddleware)
setup_exception_handlers(app)

# CORS — allow the frontend domain + localhost for development
# On Railway, NEXT_PUBLIC_API_URL is the frontend URL
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://*.up.railway.app",  # All Railway preview URLs
    "https://*.railway.app",
]
# Add custom domain if DOMAIN env var is set
_domain = os.getenv("DOMAIN", "")
if _domain and _domain != "localhost":
    _allowed_origins.append(f"https://{_domain}")
    _allowed_origins.append(f"http://{_domain}")

app.add_middleware(
    CORSMiddleware,
    # Allow explicit localhost origins
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://podlink-frontend-production.up.railway.app",
    ],
    # Allow all Railway subdomains via regex
    allow_origin_regex="https://.*\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/v1", tags=["Authentication"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(matches.router, prefix="/v1/matches", tags=["Matching"])
app.include_router(payments.router, prefix="/v1/payments", tags=["Payments"])
app.include_router(chat.router, prefix="/v1/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/v1/admin", tags=["Admin"])
app.include_router(agency.router, prefix="/v1/agency", tags=["Agency"])
app.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
app.include_router(marketing.router, prefix="/v1/marketing", tags=["Marketing"])


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "PodMatch.AI Core Backend",
        "version": "1.0.0",
        "redis": "connected" if settings.REDIS_URL else "disabled",
        "ml_service": settings.ML_SERVICE_URL,
    }


@app.get("/health")
def health_check():
    """Railway health check endpoint."""
    return {"status": "ok"}
