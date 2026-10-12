import uuid
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import crud_conversation
from app.core.realtime import manager
from app.core.security import decode_access_token

router = APIRouter()

async def get_current_user_ws(token: str, db: Session):
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    from app.crud.crud_user import get_user
    user = get_user(db, user_id=user_id)
    if not user:
        return None
    token_tv = payload.get("tv")
    if token_tv is not None and getattr(user, "token_version", None) is not None:
        if token_tv != user.token_version:
            return None
    return user

@router.websocket("/ws/notifications")
@router.websocket("/ws/notifications/")
@router.websocket("/ws/user")
@router.websocket("/ws/user/")
async def notifications_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(deps.get_db)
):
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    from app.crud.crud_team import get_user_teams
    teams = get_user_teams(db, user.id)
    team_ids = [t.id for t in teams]

    connection_id = str(uuid.uuid4())
    await manager.connect_user(websocket, user.id, user.username, connection_id, team_ids=team_ids)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(connection_id)

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    conversation_id: str, 
    token: str = Query(...),
    db: Session = Depends(deps.get_db)
):
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=1008)
        return
        
    # Check authorization
    conv = crud_conversation.get_conversation(db, conversation_id)
    if not conv:
        await websocket.close(code=1008)
        return
        
    participant = crud_conversation.get_participant(db, conversation_id, user.id)
    if not participant:
        await websocket.close(code=1008)
        return

    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, conversation_id, user.id, user.username, connection_id)
    
    # Broadcast presence.joined
    await manager.broadcast_to_conversation(conversation_id, {
        "event": "presence.joined",
        "conversation_id": conversation_id,
        "user_id": user.id,
        "user_name": user.username
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                event = message.get("event")
                if event in ["typing.started", "typing.stopped"]:
                    await manager.broadcast_to_conversation(conversation_id, {
                        "event": event,
                        "conversation_id": conversation_id,
                        "user_id": user.id,
                        "user_name": user.username
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(connection_id, conversation_id)
        # Broadcast presence.left
        has_other_connections = False
        for c_id in manager.conversation_subscriptions.get(conversation_id, []):
            if manager.connection_users.get(c_id) == user.id:
                has_other_connections = True
                break
                
        if not has_other_connections:
            await manager.broadcast_to_conversation(conversation_id, {
                "event": "presence.left",
                "conversation_id": conversation_id,
                "user_id": user.id,
                "user_name": user.username
            })
            # Clean up stale typing state
            await manager.broadcast_to_conversation(conversation_id, {
                "event": "typing.stopped",
                "conversation_id": conversation_id,
                "user_id": user.id,
                "user_name": user.username
            })



