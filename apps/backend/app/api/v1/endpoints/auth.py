from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps, auth_deps
from app.core import security
from app.core.config import settings
from app.models.user import User, UserRole
from pydantic import BaseModel, EmailStr
from datetime import datetime

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
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
def create_user(user_in: UserCreate, db: Session = Depends(deps.get_db)) -> Any:
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
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
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
