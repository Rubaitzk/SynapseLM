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
    # Verify user is in the team
    membership = crud_team.get_team_membership(db, team_id=conv_in.team_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to create conversations in this team")
    
    return crud_conversation.create_conversation(db, conv_in=conv_in, creator_id=current_user.id)

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    return check_conversation_access(db, conversation_id, current_user.id)

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    conv = check_conversation_access(db, conversation_id, current_user.id)
    
    # In a real app, only owner/admin might be able to delete. For now, any participant can.
    crud_conversation.delete_conversation(db, conversation_id)
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
    
    # Verify target user is in the team
    membership = crud_team.get_team_membership(db, team_id=conv.team_id, user_id=user_id)
    if not membership:
        raise HTTPException(status_code=400, detail="User is not a member of the team")
        
    existing = crud_conversation.get_participant(db, conversation_id, user_id)
    if existing:
        raise HTTPException(status_code=400, detail="User is already a participant")
        
    return crud_conversation.add_participant(db, conversation_id, user_id)

@router.delete("/{conversation_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(
    conversation_id: str,
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    check_conversation_access(db, conversation_id, current_user.id)
    crud_conversation.remove_participant(db, conversation_id, user_id)
    return None

# Messages
@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    check_conversation_access(db, conversation_id, current_user.id)
    return crud_conversation.create_message(db, conversation_id, message_in, sender_id=current_user.id)

@router.get("/{conversation_id}/messages", response_model=PaginatedMessages)
def get_messages(
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
