import asyncio
from app.api.deps import get_db
from app.models.database import SessionLocal
from app.models.user import User
from app.models.matches import Match

def test():
    db = SessionLocal()
    # Test if in_(["1"]) works
    users = db.query(User).filter(User.id.in_(["1"])).all()
    print("Users found by string in_:", len(users))
    
    # Check what user_id is passed as
    match = Match(user_one_id="100", user_two_id="200", is_active=True)
    print("match user_one_id:", type(match.user_one_id))

test()
