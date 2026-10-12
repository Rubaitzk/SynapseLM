import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
import redis.asyncio as redis
from fastapi import WebSocket
from app.core.config import settings

logger = logging.getLogger("synapselm.realtime")

class RealtimeManager:
    def __init__(self):
        # connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # conversation_id -> list of connection_ids
        self.conversation_subscriptions: Dict[str, List[str]] = {}
        # user_id -> list of connection_ids
        self.user_subscriptions: Dict[str, List[str]] = {}
        # team_id -> list of connection_ids
        self.team_subscriptions: Dict[str, List[str]] = {}
        # connection_id -> user_id
        self.connection_users: Dict[str, str] = {}
        # user_id -> dict of user info
        self.user_info: Dict[str, dict] = {}
        
        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5.0,
            retry_on_timeout=True
        )
        
    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str, user_name: str, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        self.user_info[user_id] = {"id": user_id, "name": user_name}
        
        if conversation_id not in self.conversation_subscriptions:
            self.conversation_subscriptions[conversation_id] = []
        self.conversation_subscriptions[conversation_id].append(connection_id)

        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        self.user_subscriptions[user_id].append(connection_id)

    async def connect_user(self, websocket: WebSocket, user_id: str, user_name: str, connection_id: str, team_ids: Optional[List[str]] = None):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        self.user_info[user_id] = {"id": user_id, "name": user_name}

        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = []
        self.user_subscriptions[user_id].append(connection_id)

        if team_ids:
            for t_id in team_ids:
                if t_id not in self.team_subscriptions:
                    self.team_subscriptions[t_id] = []
                self.team_subscriptions[t_id].append(connection_id)
        
    def disconnect(self, connection_id: str, conversation_id: Optional[str] = None):
        user_id = self.connection_users.pop(connection_id, None)
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if conversation_id and conversation_id in self.conversation_subscriptions:
            if connection_id in self.conversation_subscriptions[conversation_id]:
                self.conversation_subscriptions[conversation_id].remove(connection_id)
            if not self.conversation_subscriptions[conversation_id]:
                del self.conversation_subscriptions[conversation_id]
        if user_id and user_id in self.user_subscriptions:
            if connection_id in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].remove(connection_id)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]
        for t_id in list(self.team_subscriptions.keys()):
            if connection_id in self.team_subscriptions[t_id]:
                self.team_subscriptions[t_id].remove(connection_id)
            if not self.team_subscriptions[t_id]:
                del self.team_subscriptions[t_id]
        # Clean up user_info if no remaining connections for this user
        if user_id and user_id not in self.connection_users.values():
            self.user_info.pop(user_id, None)

    async def broadcast_to_conversation(self, conversation_id: str, message: dict):
        try:
            await self.redis.publish(f"conversation:{conversation_id}", json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish message to Redis for conversation {conversation_id}: {type(e).__name__}")

    async def broadcast_to_user(self, user_id: str, message: dict):
        try:
            await self.redis.publish(f"user:{user_id}", json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish message to Redis for user {user_id}: {type(e).__name__}")

    async def broadcast_to_team(self, team_id: str, message: dict):
        try:
            await self.redis.publish(f"team:{team_id}", json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish message to Redis for team {team_id}: {type(e).__name__}")

    async def listen_to_redis(self):
        """Listen to Redis Pub/Sub events with automatic reconnection and backoff."""
        retry_delay = 1
        while True:
            pubsub = self.redis.pubsub()
            try:
                await pubsub.psubscribe("conversation:*", "user:*", "team:*")
                logger.info("Successfully subscribed to Redis channels: conversation:*, user:*, team:*")
                retry_delay = 1
                
                async for message in pubsub.listen():
                    if message["type"] == "pmessage":
                        channel = message["channel"]
                        data = json.loads(message["data"])
                        channel_parts = channel.split(":")
                        if len(channel_parts) > 1:
                            prefix = channel_parts[0]
                            target_id = channel_parts[1]
                            conn_ids = []
                            if prefix == "conversation":
                                conn_ids = self.conversation_subscriptions.get(target_id, [])
                            elif prefix == "user":
                                conn_ids = self.user_subscriptions.get(target_id, [])
                            elif prefix == "team":
                                conn_ids = self.team_subscriptions.get(target_id, [])
                            
                            for conn_id in conn_ids:
                                ws = self.active_connections.get(conn_id)
                                if ws:
                                    try:
                                        await ws.send_json(data)
                                    except Exception:
                                        pass
            except asyncio.CancelledError:
                try:
                    await pubsub.punsubscribe("conversation:*", "user:*", "team:*")
                    if hasattr(pubsub, "aclose"):
                        await pubsub.aclose()
                    else:
                        await pubsub.close()
                except Exception:
                    pass
                break
            except Exception as e:
                logger.warning(
                    f"Redis pubsub connection lost ({type(e).__name__}). Reconnecting in {retry_delay}s..."
                )
                try:
                    if hasattr(pubsub, "aclose"):
                        await pubsub.aclose()
                    else:
                        await pubsub.close()
                except Exception:
                    pass
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)

manager = RealtimeManager()
