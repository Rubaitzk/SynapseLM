import json
import asyncio
from typing import Dict, List, Any
import redis.asyncio as redis
from fastapi import WebSocket
from app.core.config import settings

import os

class RealtimeManager:
    def __init__(self):
        # connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # conversation_id -> list of connection_ids
        self.conversation_subscriptions: Dict[str, List[str]] = {}
        # connection_id -> user_id
        self.connection_users: Dict[str, str] = {}
        # user_id -> dict of user info
        self.user_info: Dict[str, dict] = {}
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str, user_name: str, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        self.user_info[user_id] = {"id": user_id, "name": user_name}
        
        if conversation_id not in self.conversation_subscriptions:
            self.conversation_subscriptions[conversation_id] = []
        self.conversation_subscriptions[conversation_id].append(connection_id)
        
    def disconnect(self, connection_id: str, conversation_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_users:
            del self.connection_users[connection_id]
        if conversation_id in self.conversation_subscriptions:
            if connection_id in self.conversation_subscriptions[conversation_id]:
                self.conversation_subscriptions[conversation_id].remove(connection_id)
            if not self.conversation_subscriptions[conversation_id]:
                del self.conversation_subscriptions[conversation_id]

    async def broadcast_to_conversation(self, conversation_id: str, message: dict):
        # Publish to Redis so all workers get it
        await self.redis.publish(f"conversation:{conversation_id}", json.dumps(message))

    async def listen_to_redis(self):
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("conversation:*")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    conv_id = channel.split(":")[1]
                    
                    if conv_id in self.conversation_subscriptions:
                        for conn_id in self.conversation_subscriptions[conv_id]:
                            ws = self.active_connections.get(conn_id)
                            if ws:
                                try:
                                    await ws.send_json(data)
                                except Exception:
                                    pass
        except asyncio.CancelledError:
            await pubsub.punsubscribe("conversation:*")

manager = RealtimeManager()
