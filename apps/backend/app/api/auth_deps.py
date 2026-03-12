from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.api import deps
from app.models.user import User, UserRole
from pydantic import BaseModel

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/v1/login/access-token")

class TokenPayload(BaseModel):
    sub: str = None

def get_current_user(
    db: Session = Depends(deps.get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, Exception) as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    return user

def get_current_user_ws(
    db: Session = Depends(deps.get_db), token: str = None
) -> User:
    """Authentication for WebSockets where tokens are often passed as query parameters."""
    if not token:
        raise HTTPException(status_code=403, detail="Missing WebSocket token")
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, Exception):
        raise HTTPException(status_code=403, detail="Invalid WebSocket token")
        
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return user
