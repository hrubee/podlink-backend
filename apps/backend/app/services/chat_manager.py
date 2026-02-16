import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
import redis.asyncio as redis
from app.core.config import settings

class ChatConnectionManager:
    def __init__(self, redis_url: str):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis = redis.from_url(redis_url)
        self.pubsub_task = None

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Start a single PubSub listener for the entire instance if not running
        if self.pubsub_task is None:
            self.pubsub_task = asyncio.create_task(self._global_listen())

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def _global_listen(self):
        """Single global loop listening to pattern-based messages for ALL users on this pod."""
        ps = self.redis.pubsub()
        await ps.psubscribe("user_messages:*")
        
        try:
            async for message in ps.listen():
                if message["type"] == "pmessage":
                    # Channel format: user_messages:<user_id>
                    channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    target_user_id = channel.split(":")[-1]
                    
                    data = json.loads(message["data"])
                    
                    # Deliver if user is connected locally
                    if target_user_id in self.active_connections:
                        for connection in self.active_connections[target_user_id]:
                            try:
                                await connection.send_json(data)
                            except Exception:
                                pass
        except Exception as e:
            print(f"Global Redis Listener Error: {e}")
            self.pubsub_task = None # Allow restart

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Publishes a message to Redis so it reaches the user regardless of instance."""
        await self.redis.publish(f"user_messages:{user_id}", json.dumps(message))

# Global manager instance
manager = ChatConnectionManager(settings.REDIS_URL)
