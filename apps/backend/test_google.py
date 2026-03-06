import os
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-not-real-32chars!")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ci.db")

from app.models.user import User, UserRole
from app.models.marketing import WaitlistEntry
from app.models.database import SessionLocal
import traceback

print("Testing user creation...")
db = SessionLocal()
try:
    email = "testgoogle500_2@example.com"
    name = "Test Google"
    user_role = "guest"
    
    # Simulate the code failing:
    user = User(
        email=email,
        hashed_password="fake",
        full_name=name,
        role=user_role,
    )
    db.add(user)

    waitlist_entry = db.query(WaitlistEntry).filter(WaitlistEntry.email == email).first()
    if not waitlist_entry:
        new_waitlist = WaitlistEntry(
            email=email,
            fullName=name,
            role_interest=str(user_role.value) if hasattr(user_role, 'value') else str(user_role)
        )
        db.add(new_waitlist)
        
    db.commit()
    print("Success!")
except Exception as e:
    print("Exception!")
    traceback.print_exc()
finally:
    db.close()
