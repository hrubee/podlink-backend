
import sys
import os
import random
from sqlalchemy.orm import Session

# Add apps/backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import SessionLocal, engine
from app.models.user import User, UserRole, Base
from app.models.agency import Agency, agency_members
from app.models.matches import Interaction, Match
from app.core.security import get_password_hash

# 500 Demo Accounts Generator
TOPICS_POOL = [
    "AI", "Machine Learning", "Blockchain", "SaaS", "Fintech", "Healthtech", 
    "Longevity", "Biohacking", "Mental Health", "Fitness", "Nutrition",
    "Real Estate", "Venture Capital", "Fundraising", "Leadership", "Marketing",
    "E-commerce", "Sustainability", "Cybersecurity", "Gaming", "Education",
    "Self Improvement", "History", "True Crime", "Comedy", "Politics",
    "Art", "Design", "Product Management", "Software Development"
]

LOCATIONS = ["San Francisco, CA", "New York, NY", "Austin, TX", "London, UK", "Berlin, DE", "Toronto, CA", "Miami, FL", "Seattle, WA"]
AUDIENCES = ["Entrepreneurs", "Tech Enthusiasts", "Health Conscious Individuals", "Investors", "Developers", "General Public"]

def generate_mass_demo_data(count=500):
    db = SessionLocal()
    try:
        password = get_password_hash("testpassword123")
        
        print(f"Generating {count} demo accounts...")
        
        for i in range(count):
            role = random.choice([UserRole.HOST, UserRole.GUEST])
            email = f"demo_user_{i}@example.com"
            
            # Skip if exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                continue
                
            first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            topics = random.sample(TOPICS_POOL, k=random.randint(3, 6))
            
            # Metadata for role
            host_details = {}
            guest_details = {}
            
            if role == UserRole.HOST:
                pod_names = ["Talks", "Insights", "Deep Dive", "Hour", "Show", "Conversations", "Cast"]
                host_details = {
                    "podcast_name": f"The {random.choice(topics)} {random.choice(pod_names)}",
                    "podcast_desc": f"Exploring the intersection of {topics[0]} and {topics[1]}."
                }
                bio = f"Host of {host_details['podcast_name']}. I've interviewed over 100 experts in {topics[0]}."
            else:
                guest_details = {
                    "expertise_areas": f"{topics[0]} and {topics[1]}",
                    "topics_to_discuss": f"Future of {topics[2]}, scaling {topics[0]} companies."
                }
                bio = f"Specialist in {topics[0]} with 10+ years of experience. Excited to share insights about {topics[1]}."

            user = User(
                email=email,
                hashed_password=password,
                full_name=full_name,
                role=role,
                bio=bio,
                topics=topics,
                target_audience=random.choice(AUDIENCES),
                location=random.choice(LOCATIONS),
                host_details=host_details,
                guest_details=guest_details,
                onboarded=True,
                is_public=True
            )
            
            db.add(user)
            
            if (i + 1) % 100 == 0:
                db.commit()
                print(f"Committed {i + 1} users...")
                
        db.commit()
        print("Mass seeding complete!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding mass data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_mass_demo_data(500)
