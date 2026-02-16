from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps, auth_deps
from app.models.user import User, UserRole
from app.services.agency import AgencyService
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class AgencyCreate(BaseModel):
    name: str
    website: Optional[str] = None

class ClientOnboard(BaseModel):
    email: str
    full_name: str
    role: Optional[str] = "host"

class AgencyOut(BaseModel):
    id: int
    name: str
    slug: str
    
    class Config:
        orm_mode = True

@router.post("/create", response_model=AgencyOut)
async def create_agency(
    agency_in: AgencyCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    service = AgencyService(db)
    return await service.create_agency(current_user.id, agency_in.name, agency_in.website)

@router.post("/{agency_id}/onboard-client")
async def onboard_client(
    agency_id: int,
    client_in: ClientOnboard,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    # Verify user belongs to agency or is admin
    # (Simplified check for now)
    if current_user.role != UserRole.AGENCY and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only agency accounts can onboard clients")
        
    service = AgencyService(db)
    return await service.onboard_client(agency_id, client_in.email, client_in.full_name, client_in.role)

@router.get("/{agency_id}/clients")
async def list_clients(
    agency_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    service = AgencyService(db)
    return await service.get_agency_clients(agency_id)

@router.get("/my-agencies", response_model=List[AgencyOut])
async def get_my_agencies(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    service = AgencyService(db)
    return await service.get_user_agencies(current_user.id)
    
@router.get("/public/{slug}", response_model=dict)
async def get_public_agency(
    slug: str,
    db: Session = Depends(deps.get_db)
):
    """
    Publicly accessible agency information by slug.
    """
    from app.models.agency import Agency
    agency = db.query(Agency).filter(Agency.slug == slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
        
    return {
        "id": agency.id,
        "name": agency.name,
        "slug": agency.slug,
        "website": agency.website,
        "logo_url": agency.logo_url,
        "clients": [
            {
                "id": client.id,
                "full_name": client.full_name,
                "role": client.role,
                "avatar_url": client.avatar_url,
                "bio": client.bio
            } for client in agency.clients if client.is_public and client.is_active
        ]
    }
