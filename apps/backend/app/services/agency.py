from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.agency import Agency, agency_members
from app.models.user import User, UserRole
from fastapi import HTTPException

class AgencyService:
    def __init__(self, db: Session):
        self.db = db

    async def create_agency(self, owner_id: int, name: str, website: str = None):
        # Ensure user exists and is not already owning an agency (optional rule)
        owner = self.db.query(User).filter(User.id == owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Create agency
        slug = name.lower().replace(" ", "-")
        agency = Agency(name=name, owner_id=owner_id, slug=slug, website=website)
        self.db.add(agency)
        
        # Change owner role to AGENCY if not already admin
        if owner.role not in [UserRole.ADMIN, UserRole.AGENCY]:
            owner.role = UserRole.AGENCY
            
        self.db.commit()
        self.db.refresh(agency)
        
        # Add owner as a member with 'manager' role in the association table
        # Note: association table insert
        from sqlalchemy import insert
        self.db.execute(insert(agency_members).values(agency_id=agency.id, user_id=owner_id, role="manager"))
        self.db.commit()
        
        return agency

    async def onboard_client(self, agency_id: int, client_email: str, client_name: str, role: str = "host"):
        """Creates a new user profile managed by the agency."""
        # 1. Check if user already exists
        existing_user = self.db.query(User).filter(User.email == client_email).first()
        if existing_user:
            if existing_user.agency_id:
                raise HTTPException(status_code=400, detail="User already managed by an agency")
            existing_user.agency_id = agency_id
            existing_user.role = role
        else:
            # Create new shadow user
            from app.core import security
            dummy_password = security.get_password_hash("ShadowUser123!") # Agency usually manages this
            new_user = User(
                email=client_email,
                full_name=client_name,
                hashed_password=dummy_password,
                role=role,
                agency_id=agency_id
            )
            self.db.add(new_user)
            existing_user = new_user
            
        self.db.commit()
        self.db.refresh(existing_user)
        return existing_user

    async def get_agency_clients(self, agency_id: int):
        return self.db.query(User).filter(User.agency_id == agency_id).all()

    async def get_user_agencies(self, user_id: int):
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.agencies if user else []
