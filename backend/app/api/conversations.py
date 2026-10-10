from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_conversation, crud_team
from app.schemas.conversation import (
    ConversationCreate, 
    ConversationResponse, 
    ConversationParticipantResponse,
    MessageCreate,
    MessageResponse,
    PaginatedMessages
)
from app.schemas.user import UserResponse

router = APIRouter()

def check_conversation_access(db: Session, conversation_id: str, user_id: str):
    conv = crud_conversation.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    participant = crud_conversation.get_participant(db, conversation_id, user_id)
    if not participant:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    return conv

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    if conv_in.team_id:
        # Verify user is in the team
        membership = crud_team.get_team_membership(db, team_id=conv_in.team_id, user_id=current_user.id)
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized to create conversations in this team")
    
    return crud_conversation.create_conversation(db, conv_in=conv_in, creator_id=current_user.id)


@router.get("/", response_model=List[ConversationResponse])
def get_user_conversations(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    return crud_conversation.get_user_conversations(db, current_user.id)

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    return check_conversation_access(db, conversation_id, current_user.id)

@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    conv_in: __import__('app.schemas.conversation', fromlist=['ConversationUpdate']).ConversationUpdate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    # Check if user is owner/admin of the team to modify AI config, or owner of individual chat
    if conv.team_id:
        from app.models.team import Role
        membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=current_user.id)
        if not membership or membership.role not in [Role.owner, Role.admin]:
            raise HTTPException(status_code=403, detail="Not authorized to modify conversation settings")
    else:
        if conv.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify conversation settings")
        
    conv = crud_conversation.update_conversation(db, conv, conv_in)
    return conv

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    background_tasks: __import__('fastapi').BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    # Restrict to owner/admin
    if conv.team_id:
        from app.models.team import Role
        membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=current_user.id)
        if not membership or membership.role not in [Role.owner, Role.admin]:
            raise HTTPException(status_code=403, detail="Not authorized to delete conversation")
    else:
        if conv.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete conversation")
        
    crud_conversation.delete_conversation(db, conversation_id)
    
    # Broadcast deletion to kick any active websockets
    await __import__('app.core.realtime', fromlist=['manager']).manager.broadcast_to_conversation(conversation_id, {
        "event": "conversation.deleted",
        "conversation_id": conversation_id
    })
    
    return None

# Participants
@router.get("/{conversation_id}/participants", response_model=List[ConversationParticipantResponse])
def get_participants(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    check_conversation_access(db, conversation_id, current_user.id)
    return crud_conversation.get_participants(db, conversation_id)

@router.post("/{conversation_id}/participants/{user_id}", response_model=ConversationParticipantResponse)
def add_participant(
    conversation_id: str,
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    if not conv.team_id:
        raise HTTPException(status_code=400, detail="Cannot add participants directly to an individual conversation in Phase 1.5.")

    # Verify that the current user is an admin or owner of the team
    from app.models.team import Role
    current_membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=current_user.id)
    if not current_membership or current_membership.role not in [Role.owner, Role.admin]:
        raise HTTPException(status_code=403, detail="Not enough permissions to add participants")

    # Verify target user is in the team
    membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=user_id)
    if not membership:
        raise HTTPException(status_code=400, detail="User is not a member of the team")
        
    existing = crud_conversation.get_participant(db, conversation_id, user_id)
    if existing:
        raise HTTPException(status_code=400, detail="User is already a participant")
        
    return crud_conversation.add_participant(db, conversation_id, user_id)

@router.delete("/{conversation_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(
    conversation_id: str,
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    # If a user is not removing themselves, they must be an admin/owner
    if current_user.id != user_id:
        if not conv.team_id:
            raise HTTPException(status_code=403, detail="Cannot remove other participants from an individual conversation.")
        from app.models.team import Role
        current_membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=current_user.id)
        if not current_membership or current_membership.role not in [Role.owner, Role.admin]:
            raise HTTPException(status_code=403, detail="Not enough permissions to remove participants")

    crud_conversation.remove_participant(db, conversation_id, user_id)
    
    # Broadcast to kick active websocket if they are connected
    await __import__('app.core.realtime', fromlist=['manager']).manager.broadcast_to_conversation(conversation_id, {
        "event": "participant.removed",
        "conversation_id": conversation_id,
        "user_id": user_id
    })
    
    return None

from fastapi import BackgroundTasks
from app.core.realtime import manager
import asyncio

# Messages
@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    from app.models.conversation import LifecycleState
    if conv.lifecycle_state != LifecycleState.active:
        raise HTTPException(status_code=400, detail="Cannot send messages to an archived or deleted conversation")
    
    # 1. Persist user message
    user_msg = crud_conversation.create_message(db, conversation_id, message_in, sender_id=current_user.id)
    
    message_data = MessageResponse.model_validate(user_msg).model_dump(mode='json')
    
    # 1.5 Broadcast message
    # We use asyncio.create_task to run this without blocking, or await it
    await manager.broadcast_to_conversation(conversation_id, {
        "event": "message.created",
        "conversation_id": conversation_id,
        "message": message_data
    })
    
    # 2. Trigger AI orchestrator in background
    from app.services.llm.orchestrator import generate_assistant_response
    background_tasks.add_task(generate_assistant_response, db, conversation_id)
    
    return user_msg

@router.get("/{conversation_id}/messages", response_model=PaginatedMessages)
async def get_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    check_conversation_access(db, conversation_id, current_user.id)
    skip = (page - 1) * size
    items, total = crud_conversation.get_messages(db, conversation_id, skip=skip, limit=size)
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }

@router.get("/{conversation_id}/presence")
async def get_conversation_presence(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    check_conversation_access(db, conversation_id, current_user.id)
    active_users = []
    conns = manager.conversation_subscriptions.get(conversation_id, [])
    user_ids = set()
    for c_id in conns:
        uid = manager.connection_users.get(c_id)
        if uid and uid not in user_ids:
            user_ids.add(uid)
            active_users.append(manager.user_info[uid])
            
    return {"active_users": active_users}

# Shares Management

from app.schemas.share import ShareCreate, ConversationShareResponse
from app.crud import crud_share

@router.post("/{conversation_id}/shares", response_model=ConversationShareResponse)
def create_share(
    conversation_id: str,
    share_in: ShareCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can create shares")
    if conv.parent_conversation_id:
        raise HTTPException(status_code=400, detail="Cannot create a share for a branch")
        
    share, token = crud_share.create_share(db, conversation_id, current_user.id, share_in.expires_in_seconds)
    # the token is returned once
    resp = ConversationShareResponse.model_validate(share)
    resp.share_token = token
    return resp

@router.get("/{conversation_id}/shares", response_model=List[ConversationShareResponse])
def get_shares(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can view shares")
        
    shares = crud_share.get_conversation_shares(db, conversation_id)
    return shares

@router.post("/{conversation_id}/shares/{share_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(
    conversation_id: str,
    share_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can revoke shares")
        
    share = crud_share.get_share(db, share_id)
    if not share or share.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Share not found")
        
    crud_share.revoke_share(db, share)
    return None

# Access Requests Management

from app.schemas.request import AccessRequestResponse
from app.crud import crud_request

@router.get("/{conversation_id}/requests", response_model=List[AccessRequestResponse])
def get_requests(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can view requests")
        
    requests = crud_request.get_conversation_requests(db, conversation_id)
    return requests

@router.post("/{conversation_id}/requests/{request_id}/accept", response_model=ConversationParticipantResponse)
async def accept_request(
    conversation_id: str,
    request_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can accept requests")
        
    # use for_update to lock the request
    req = db.query(__import__('app.models.conversation', fromlist=['ConversationAccessRequest']).ConversationAccessRequest).filter_by(id=request_id).with_for_update().first()
    if not req or req.share.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Request not found")
        
    try:
        req = crud_request.accept_request(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    participant = crud_conversation.get_participant(db, conversation_id, req.requester_id)
    return participant

@router.post("/{conversation_id}/requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_request(
    conversation_id: str,
    request_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    if conv.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can reject requests")
        
    req = db.query(__import__('app.models.conversation', fromlist=['ConversationAccessRequest']).ConversationAccessRequest).filter_by(id=request_id).with_for_update().first()
    if not req or req.share.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Request not found")
        
    try:
        crud_request.reject_request(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return None

