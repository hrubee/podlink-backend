
import sys
import os
from sqlalchemy.orm import Session

# Add apps/backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import SessionLocal
from app.models.user import User

def remove_dummy_users():
    db = SessionLocal()
    try:
        dummy_emails = [
            "tech_host@example.com",
            "health_host@example.com",
            "fitness_host@example.com",
            "ai_expert@example.com",
            "nutrition_pro@example.com",
            "founder_guest@example.com",
            "mindset_coach@example.com"
        ]
        
        print(f"Checking for {len(dummy_emails)} dummy users...")
        
        # Check existing users to delete
        users_to_delete = db.query(User).filter(User.email.in_(dummy_emails)).all()
        
        if not users_to_delete:
            print("No dummy users found to delete.")
            return

        print(f"Found {len(users_to_delete)} users to delete.")
        
        # Delete them
        for user in users_to_delete:
            db.delete(user)
            print(f"Deleted user: {user.email}")
            
        db.commit()
        print("All dummy users removed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error removing dummy users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    remove_dummy_users()
