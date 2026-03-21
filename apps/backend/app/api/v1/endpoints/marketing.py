from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.models.marketing import WaitlistEntry
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()

class WaitlistCreate(BaseModel):
    email: EmailStr
    fullName: Optional[str] = None
    role_interest: Optional[str] = "both"

@router.post("/join", status_code=status.HTTP_201_CREATED)
def join_waitlist(data: WaitlistCreate, db: Session = Depends(deps.get_db)):
    from app.models.user import User
    
    # Check if they already have an actual account
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        from app.core import security
        from app.core.config import settings
        from datetime import timedelta
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = security.create_access_token(existing_user.id, expires_delta=access_token_expires)
        return {
            "message": "User already has an account", 
            "status": "user_exists",
            "access_token": token,
            "user": {
                "id": existing_user.id,
                "email": existing_user.email,
                "full_name": existing_user.full_name,
                "role": existing_user.role,
                "onboarded": existing_user.onboarded
            }
        }

    # Check if already exists in waitlist
    existing = db.query(WaitlistEntry).filter(WaitlistEntry.email == data.email).first()
    if existing:
        return {"message": "Already on the waitlist", "status": "exists"}
    
    new_entry = WaitlistEntry(
        email=data.email,
        fullName=data.fullName,
        role_interest=data.role_interest
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return {"message": "Successfully joined the waitlist", "status": "success"}
