import redis
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.matches import Interaction, Match, InteractionType
from app.core.config import settings

class MatchingService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.match_limit = 30
        self.limit_window_days = 30

    async def handle_like(self, actor_id: str, target_id: str) -> bool:
        """Processes a like and returns True if it results in a mutual match."""
        # 1. Check if target has already liked actor (Mutual Match)
        target_liked_key = f"likes:{target_id}:{actor_id}"
        is_mutual = self.redis.exists(target_liked_key)

        # 2. Log interaction to DB (for ML/History)
        interaction = Interaction(
            actor_id=actor_id,
            target_id=target_id,
            interaction_type=InteractionType.LIKE
        )
        self.db.add(interaction)

        # 3. Store like in Redis for fast lookup (TTL 30 days)
        actor_liked_key = f"likes:{actor_id}:{target_id}"
        self.redis.setex(actor_liked_key, 2592000, "1") # 30 days

        if is_mutual:
            # 4. Enforce Match Limits
            if not await self._can_match(actor_id) or not await self._can_match(target_id):
                return False # Or raise a specific "Limit Exceeded" exception

            # 5. Create Match
            await self._create_match(actor_id, target_id)
            return True
        
        self.db.commit()
        return False

    async def _can_match(self, user_id: str) -> bool:
        """Checks if user is within their 30 rolling match limit."""
        limit_key = f"limits:matches:{user_id}"
        current_count = self.redis.get(limit_key)
        if current_count and int(current_count) >= self.match_limit:
            return False
        return True

    async def _create_match(self, user_a: str, user_b: str):
        # Prevent duplicate active matches
        match = Match(user_one_id=user_a, user_two_id=user_b)
        self.db.add(match)
        
        # Increment rolling limit in Redis
        for uid in [user_a, user_b]:
            limit_key = f"limits:matches:{uid}"
            count = self.redis.incr(limit_key)
            if count == 1:
                self.redis.expire(limit_key, 2592000) # 30 days window

        # Cache match in Redis for performance lookup
        match_cache_key = f"active_matches:{user_a}"
        self.redis.sadd(match_cache_key, user_b)
        self.redis.sadd(f"active_matches:{user_b}", user_a)
        
        self.db.commit()

    async def unmatch(self, user_id: str, target_id: str):
        match = self.db.query(Match).filter(
            ((Match.user_one_id == user_id) & (Match.user_two_id == target_id)) |
            ((Match.user_one_id == target_id) & (Match.user_two_id == user_id)),
            Match.is_active == True
        ).first()

        if match:
            match.is_active = False
            self.redis.srem(f"active_matches:{user_id}", target_id)
            self.redis.srem(f"active_matches:{target_id}", user_id)
            self.db.commit()

    async def get_active_matches(self, user_id: str) -> List[str]:
        """Fast lookup of active match IDs from Redis cache, falls back to DB."""
        raw = self.redis.smembers(f"active_matches:{user_id}")
        if raw:
            # Real Redis returns bytes; NoOpRedis returns set() of strings
            return [m.decode('utf-8') if isinstance(m, bytes) else str(m) for m in raw]
        
        # Fallback: query DB directly (when Redis is cold or unavailable)
        from app.models.matches import Match
        matches = self.db.query(Match).filter(
            ((Match.user_one_id == user_id) | (Match.user_two_id == user_id)),
            Match.is_active == True
        ).all()
        return [
            m.user_two_id if m.user_one_id == user_id else m.user_one_id
            for m in matches
        ]

