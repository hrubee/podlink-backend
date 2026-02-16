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
    # Check if already exists
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
