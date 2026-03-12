
import sys
import os
import random
import json
import asyncio
import time
from sqlalchemy.orm import Session

# Add apps/backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import SessionLocal, engine
from app.models.user import User, UserRole, Base
from app.models.matches import Match, Interaction, InteractionType
from app.models.chat import ChatMessage

def stress_test_messaging(match_count=100, message_count=500):
    db = SessionLocal()
    try:
        # 1. Fetch some demo users
        demo_hosts = db.query(User).filter(User.role == UserRole.HOST).limit(50).all()
        demo_guests = db.query(User).filter(User.role == UserRole.GUEST).limit(50).all()
        
        if not demo_hosts or not demo_guests:
            print("Not enough demo users found. Please run seed_mass.py first.")
            return

        print(f"Creating {match_count} mutual matches...")
        matches_created = []
        
        for i in range(match_count):
            host = random.choice(demo_hosts)
            guest = random.choice(demo_guests)
            
            # Create a match
            new_match = Match(
                user_one_id=str(host.id),
                user_two_id=str(guest.id),
                is_active=True
            )
            db.add(new_match)
            matches_created.append((host.id, guest.id))
            
            # Create mutual interactions
            i1 = Interaction(actor_id=str(host.id), target_id=str(guest.id), interaction_type=InteractionType.LIKE)
            i2 = Interaction(actor_id=str(guest.id), target_id=str(host.id), interaction_type=InteractionType.LIKE)
            db.add(i1)
            db.add(i2)
            
        db.commit()
        print(f"Match generation complete. Now simulating {message_count} messages...")

        start_time = time.time()
        for i in range(message_count):
            hid, gid = random.choice(matches_created)
            sender_id, receiver_id = random.choice([(hid, gid), (gid, hid)])
            
            room_id = "-".join(sorted([str(sender_id), str(receiver_id)]))
            
            msg = ChatMessage(
                sender_id=str(sender_id),
                room_id=room_id,
                content=f"Stress test message #{i}: Hey, let's record a podcast about {random.choice(['AI', 'Blockchain', 'Health'])}!"
            )
            db.add(msg)
            
            if (i+1) % 100 == 0:
                db.commit()
                print(f"Sent {i+1} messages...")

        db.commit()
        end_time = time.time()
        
        print(f"--- STRESS TEST RESULTS ---")
        print(f"Total Matches: {match_count}")
        print(f"Total Messages: {message_count}")
        print(f"Time Taken: {end_time - start_time:.2f} seconds")
        print(f"Throughput: {message_count / (end_time - start_time):.2f} messages/sec")
        print(f"---------------------------")

    except Exception as e:
        db.rollback()
        print(f"Stress test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    stress_test_messaging(100, 1000)
