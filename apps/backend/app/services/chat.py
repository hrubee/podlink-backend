from sqlalchemy.orm import Session
from app.models.chat import ChatMessage
from app.services.payments import PaymentService
from app.services.chat_manager import manager
import redis
import json

class ChatService:
    def __init__(self, db: Session, r: redis.Redis):
        self.db = db
        self.redis = r
        self.payment_service = PaymentService(db, r)

    async def send_message(self, sender_id: str, receiver_id: str, content: str):
        # 1. Match Verification (Hosts/Guests must be matched to chat)
        match_key = f"active_matches:{sender_id}"
        is_matched = self.redis.sismember(match_key, receiver_id)
        if not is_matched:
            # Check DB as fallback if Redis is cold
            from app.models.matches import Match
            match_exists = self.db.query(Match).filter(
                ((Match.user_one_id == sender_id) & (Match.user_two_id == receiver_id)) |
                ((Match.user_one_id == receiver_id) & (Match.user_two_id == sender_id)),
                Match.is_active == True
            ).first()
            if not match_exists:
                raise ValueError("Users must be matched to exchange messages.")

        # 2. Moderation check
        is_flagged = self._check_moderation(content)

        # 3. Persistence
        room_id = self._get_room_id(sender_id, receiver_id)
        message = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            is_flagged=is_flagged
        )
        self.db.add(message)
        self.db.commit()

        # 4. Distributed Broadcast via Pub/Sub
        broadcast_data = {
            "type": "new_message",
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content if not is_flagged else "[Message hidden by moderation]",
            "timestamp": message.created_at.isoformat() if message.created_at else datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_user(receiver_id, broadcast_data)
        
        # 5. Notification Trigger
        await self._trigger_notification(receiver_id, sender_id)
        
        return message

    def _get_room_id(self, user_a: str, user_b: str) -> str:
        return "-".join(sorted([user_a, user_b]))

    def _check_moderation(self, content: str) -> bool:
        banned_words = ["spam", "scam", "offensive_term"] # Expand this
        return any(word in content.lower() for word in banned_words)

    async def _trigger_notification(self, user_id: str, from_user_id: str):
        # Trigger an 'unread' count in Redis
        self.redis.hincrby(f"user:{user_id}:notifications", "unread_messages", 1)
        # In a full system, this would push to FCM/APNs or a queue for email
        pass

    async def flag_message(self, message_id: int, reason: str):
        """Admin/Moderation tool to flag a message."""
        message = self.db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if message:
            message.is_flagged = True
            message.flagged_reason = reason
            self.db.commit()
            return True
        return False
