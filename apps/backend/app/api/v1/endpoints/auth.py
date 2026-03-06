from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps, auth_deps
from app.core import security
from app.core.config import settings
from app.models.user import User, UserRole
from pydantic import BaseModel, EmailStr
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import redis
import time

router = APIRouter()


def _check_rate_limit(r: redis.Redis, key: str, max_attempts: int = 10, window_seconds: int = 900):
    """Sliding-window rate limiter. Raises 429 if limit exceeded. No-ops if Redis is unavailable."""
    from app.api.deps import NoOpRedis
    if isinstance(r, NoOpRedis):
        return  # Redis not configured — allow all (fail open)
    now = time.time()
    window_start = now - window_seconds
    r.zremrangebyscore(key, 0, window_start)
    count = r.zcard(key)
    if count >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please try again in {window_seconds // 60} minutes."
        )
    r.zadd(key, {str(now): now})
    r.expire(key, window_seconds)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.GUEST

class GoogleLogin(BaseModel):
    token: str
    role: UserRole = UserRole.GUEST

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    onboarded: bool = False

    class Config:
        from_attributes = True

@router.post("/signup", response_model=UserOut)
def create_user(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
) -> Any:
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(r, f"rate_limit:signup:{ip}")

    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="User already exists")

    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login/access-token")
def login_access_token(
    request: Request,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    r: redis.Redis = Depends(deps.get_redis)
) -> Any:
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(r, f"rate_limit:login:{ip}")

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active or user.is_deleted:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/google")
def login_with_google(
    payload: GoogleLogin, db: Session = Depends(deps.get_db)
) -> Any:
    try:
        # Verify the Google JWT token
        idinfo = id_token.verify_oauth2_token(
            payload.token, google_requests.Request(), settings.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10
        )
        email = idinfo.get("email")
        name = idinfo.get("name")
        
        if not email:
            raise HTTPException(status_code=400, detail="Google token does not contain an email")

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create user if not exists
            user_role = payload.role if payload.role else UserRole.GUEST
            user = User(
                email=email,
                hashed_password=security.get_password_hash(security.get_random_string(32)), # Random password for google users
                full_name=name,
                role=user_role,
            )
            db.add(user)

            # Auto-add them to the waitlist too (if not already there)
            from app.models.marketing import WaitlistEntry
            waitlist_entry = db.query(WaitlistEntry).filter(WaitlistEntry.email == email).first()
            if not waitlist_entry:
                new_waitlist = WaitlistEntry(
                    email=email,
                    fullName=name,
                    role_interest=str(user_role.value) if hasattr(user_role, 'value') else str(user_role)
                )
                db.add(new_waitlist)
                
            db.commit()
            db.refresh(user)

        elif not user.is_active or user.is_deleted:
            raise HTTPException(status_code=400, detail="Inactive user")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": security.create_access_token(
                user.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "onboarded": user.onboarded
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_data(
    hard_delete: bool = False,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """GDPR Compliant Deletion: Soft delete by default, Hard delete on request."""
    if hard_delete:
        db.delete(current_user)
    else:
        current_user.is_deleted = True
        current_user.deleted_at = datetime.utcnow()
        current_user.is_active = False
    
    db.commit()
    return None
