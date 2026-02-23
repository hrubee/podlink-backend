import asyncio
from app.models.database import SessionLocal
from app.api.deps import NoOpRedis
from app.models.user import User
from app.models.matches import Match
from app.services.chat import ChatService
from app.services.matching import MatchingService

async def debug_issue():
    db = SessionLocal()
    r = NoOpRedis()
    
    # 1. Clean up old mock users
    db.query(User).filter(User.email.in_(["acct1@test.com", "acct2@test.com"])).delete(synchronize_session=False)
    db.query(Match).delete(synchronize_session=False)
    db.commit()

    # 2. Create Acct 1 and 2
    u1 = User(email="acct1@test.com", hashed_password="pw", full_name="Acct 1")
    u2 = User(email="acct2@test.com", hashed_password="pw", full_name="Acct 2")
    db.add_all([u1, u2])
    db.commit()

    print(f"Acct 1 ID: {u1.id}, type: {type(u1.id)}")
    print(f"Acct 2 ID: {u2.id}, type: {type(u2.id)}")

    # 3. Acct 1 sends message to Acct 2
    chat_svc = ChatService(db, r)
    print("Simulating Account 1 sending to Account 2...")
    await chat_svc.send_message(str(u1.id), str(u2.id), "Checking Media Kit message!")

    # 4. Acct 2 views matches
    matching_svc = MatchingService(db, r)
    match_ids = await matching_svc.get_active_matches(str(u2.id))
    print(f"Raw match IDs found for Acct 2: {match_ids}, type of first: {type(match_ids[0]) if match_ids else 'none'}")

    matched_users = db.query(User).filter(User.id.in_(match_ids)).all()
    print(f"Users found via IN clause: {[u.email for u in matched_users]}")

if __name__ == "__main__":
    asyncio.run(debug_issue())
