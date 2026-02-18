import json
import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket
from app.core.config import settings


class ChatConnectionManager:
    def __init__(self, redis_url: Optional[str]):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_url = redis_url
        self.redis = None
        self.pubsub_task = None

        # Only initialise async Redis if a URL is provided
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self.redis = aioredis.from_url(redis_url)
            except Exception as e:
                print(f"[ChatManager] Redis init failed, running in local-only mode: {e}")

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

        # Start PubSub listener only if Redis is available
        if self.redis and self.pubsub_task is None:
            self.pubsub_task = asyncio.create_task(self._global_listen())

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def _global_listen(self):
        """Single global loop listening to pattern-based messages for ALL users on this pod."""
        if not self.redis:
            return
        ps = self.redis.pubsub()
        await ps.psubscribe("user_messages:*")

        try:
            async for message in ps.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    target_user_id = channel.split(":")[-1]

                    data = json.loads(message["data"])

                    if target_user_id in self.active_connections:
                        for connection in self.active_connections[target_user_id]:
                            try:
                                await connection.send_json(data)
                            except Exception:
                                pass
        except Exception as e:
            print(f"Global Redis Listener Error: {e}")
            self.pubsub_task = None  # Allow restart

    async def broadcast_to_user(self, user_id: str, message: dict):
        """
        Publishes a message via Redis pub/sub (multi-instance).
        Falls back to direct local delivery if Redis is unavailable.
        """
        if self.redis:
            try:
                await self.redis.publish(f"user_messages:{user_id}", json.dumps(message))
                return
            except Exception as e:
                print(f"[ChatManager] Redis publish failed, falling back to local: {e}")

        # Local-only fallback (single instance mode — fine for Railway)
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


# Global manager instance — uses REDIS_URL from settings (None = local-only mode)
manager = ChatConnectionManager(settings.REDIS_URL)

