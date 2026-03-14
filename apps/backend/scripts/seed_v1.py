
import sys
import os
from sqlalchemy.orm import Session
import json

# Add apps/backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import SessionLocal, engine
from app.models.user import User, UserRole, Base
from app.models.matches import Interaction, Match
from app.core.security import get_password_hash

def seed_v1_data():
    db = SessionLocal()
    try:
        # Create test password
        password = get_password_hash("testpassword123")
        
        # 1. Create a selection of Hosts
        hosts = [
            {
                "email": "tech_host@example.com",
                "full_name": "Sarah Tech",
                "bio": "I host 'The Silicon Wave', a weekly dive into AI and future startups. Seeking industry experts and founders.",
                "topics": ["AI", "Startups", "Venture Capital", "Software Engineering"],
                "target_audience": "Tech-savvy entrepreneurs and developers",
                "location": "San Francisco, CA",
                "host_details": {"podcast_name": "The Silicon Wave"}
            },
            {
                "email": "health_host@example.com",
                "full_name": "Dr. Mike Wellness",
                "bio": "Host of 'Biohacking 101'. We discuss longevity, nutrition, and mental health. Looking for doctors and researchers.",
                "topics": ["Longevity", "Nutrition", "Mental Health", "Biohacking"],
                "target_audience": "Health enthusiasts and medical professionals",
                "location": "Austin, TX",
                "host_details": {"podcast_name": "Biohacking 101"}
            },
            {
                "email": "fitness_host@example.com",
                "full_name": "Coach Alex",
                "bio": "The Peak Performance Podcast. Interviewing elite athletes and performance coaches about their rituals.",
                "topics": ["Fitness", "Sports", "Mindset", "Performance"],
                "target_audience": "Athletes and fitness addicts",
                "location": "Miami, FL",
                "host_details": {"podcast_name": "Peak Performance"}
            }
        ]
        
        # 2. Create a selection of Guests
        guests = [
            {
                "email": "ai_expert@example.com",
                "full_name": "Dr. Elena AI",
                "bio": "PhD in Machine Learning. 10 years at DeepMind. I can speak about the future of AGI and AI Ethics.",
                "topics": ["AI", "Machine Learning", "Technology", "Ethics"],
                "target_audience": "General tech audience",
                "location": "London, UK",
                "guest_details": {"expertise_areas": "Machine Learning, Neural Networks"}
            },
            {
                "email": "nutrition_pro@example.com",
                "full_name": "James Nutrition",
                "bio": "Registered Dietitian specializing in plant-based diets for elite performance. Featured in Joe Rogan and Huberman.",
                "topics": ["Nutrition", "Fitness", "Plant-based", "Performance"],
                "target_audience": "Everyone interested in health",
                "location": "New York, NY",
                "guest_details": {"expertise_areas": "Sports Nutrition"}
            },
            {
                "email": "founder_guest@example.com",
                "full_name": "Mark Founder",
                "bio": "Scaled 3 startups to 8-figure valuations. I talk about fundraising, hiring, and the 'hard things' about startups.",
                "topics": ["Entrepeneurship", "Startups", "Fundraising", "Business"],
                "target_audience": "Aspiring founders",
                "location": "Seattle, WA",
                "guest_details": {"expertise_areas": "SaaS Scaling"}
            },
            {
                "email": "mindset_coach@example.com",
                "full_name": "Sophia Mind",
                "bio": "Mindset coach for Olympic athletes. Specialized in flow states and high-pressure performance.",
                "topics": ["Mindset", "Psychology", "Sports", "Performance"],
                "target_audience": "High-performers",
                "location": "Los Angeles, CA",
                "guest_details": {"expertise_areas": "Peak Performance Psychology"}
            }
        ]
        
        all_test_users = []
        
        for h in hosts:
            user = User(
                email=h["email"],
                hashed_password=password,
                full_name=h["full_name"],
                role=UserRole.HOST,
                bio=h["bio"],
                topics=h["topics"],
                target_audience=h["target_audience"],
                location=h["location"],
                host_details=h["host_details"],
                onboarded=True,
                is_public=True
            )
            all_test_users.append(user)
            
        for g in guests:
            user = User(
                email=g["email"],
                hashed_password=password,
                full_name=g["full_name"],
                role=UserRole.GUEST,
                bio=g["bio"],
                topics=g["topics"],
                target_audience=g["target_audience"],
                location=g["location"],
                guest_details=g["guest_details"],
                onboarded=True,
                is_public=True
            )
            all_test_users.append(user)
            
        for user in all_test_users:
            existing = db.query(User).filter(User.email == user.email).first()
            if not existing:
                db.add(user)
                print(f"Adding user: {user.email}")
            else:
                print(f"User {user.email} already exists")
                
        db.commit()
        print("Seeding complete!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_v1_data()
