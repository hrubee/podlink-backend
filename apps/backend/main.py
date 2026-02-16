from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.v1.endpoints import matches, payments, chat, auth, admin, agency, discovery, users, marketing
from app.models.database import engine, Base
# Import all models to ensure they are registered with Base
from app.models.user import User
from app.models.chat import ChatMessage, ChatRoom
from app.models.safety import UserReport, AuditLog
from app.models.matches import Match
from app.models.agency import Agency
from app.models.marketing import WaitlistEntry

Base.metadata.create_all(bind=engine)

from app.core.middleware import ObservabilityMiddleware, setup_exception_handlers

app = FastAPI(title="Podcast Matching API")

# Add Observability
app.add_middleware(ObservabilityMiddleware)
setup_exception_handlers(app)

app.include_router(auth.router, prefix="/v1", tags=["Authentication"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(matches.router, prefix="/v1/matches", tags=["Matching"])
app.include_router(payments.router, prefix="/v1/payments", tags=["Payments"])
app.include_router(chat.router, prefix="/v1/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/v1/admin", tags=["Admin"])
app.include_router(agency.router, prefix="/v1/agency", tags=["Agency"])
app.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
app.include_router(marketing.router, prefix="/v1/marketing", tags=["Marketing"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Backend is online", "service": "Core Backend"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
