from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import crud_share, crud_conversation, crud_request
from app.schemas.share import SharedConversationPreviewResponse
from app.schemas.conversation import ConversationResponse
from app.schemas.request import AccessRequestResponse, AccessRequestCreate
from app.models.conversation import LifecycleState
from datetime import datetime, timezone

router = APIRouter()

@router.get("/{share_token}", response_model=SharedConversationPreviewResponse)
def preview_share(share_token: str, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_user)):
    share = crud_share.get_share_by_token(db, share_token)
    if not share or not share.is_active:
        raise HTTPException(status_code=404, detail="Share link is invalid or revoked")
    
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Share link has expired")
        
        
    from app.crud import crud_user
    owner = crud_user.get_user(db, share.conversation.owner_id) if share.conversation.owner_id else None
    
    is_owner = (current_user.id == share.conversation.owner_id)
    participant = crud_conversation.get_participant(db, share.conversation_id, current_user.id)
    is_participant = (participant is not None) or is_owner
    
    return SharedConversationPreviewResponse(
        title=share.conversation.title,
        owner_username=owner.username if owner else "Unknown",
        expires_at=share.expires_at,
        conversation_id=share.conversation_id if is_participant else None,
        is_participant=is_participant
    )

@router.post("/{share_token}/branches", response_model=ConversationResponse)
def create_branch_from_share(share_token: str, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_user)):
    share = crud_share.get_share_by_token(db, share_token)
    if not share or not share.is_active:
        raise HTTPException(status_code=404, detail="Share link is invalid or revoked")
        
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Share link has expired")
        
    # Check if recipient is already a participant
    participant = crud_conversation.get_participant(db, share.conversation_id, current_user.id)
    if participant:
        raise HTTPException(status_code=400, detail="You are already a participant in this conversation")
        
    # Create the branch
    branch = crud_conversation.create_branch(db, share.conversation_id, current_user.id, f"Branch of {share.conversation.title}")
    return branch

from app.core.realtime import manager

@router.post("/{share_token}/requests", response_model=AccessRequestResponse)
async def request_access(share_token: str, req_in: AccessRequestCreate, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_user)):
    share = crud_share.get_share_by_token(db, share_token)
    if not share or not share.is_active:
        raise HTTPException(status_code=404, detail="Share link is invalid or revoked")
        
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Share link has expired")
        
    branch = crud_conversation.get_conversation(db, req_in.branch_conversation_id)
    if not branch or branch.owner_id != current_user.id or branch.parent_conversation_id != share.conversation_id:
        raise HTTPException(status_code=403, detail="Invalid branch for access request")
        
    if branch.lifecycle_state != LifecycleState.active:
        raise HTTPException(status_code=400, detail="Branch is not active")
        
    try:
        req = crud_request.create_request(db, share.id, current_user.id, branch.id)
        
        # Broadcast request.created to the parent conversation
        await manager.broadcast_to_conversation(share.conversation_id, {
            "event": "request.created",
            "conversation_id": share.conversation_id,
            "request_id": req.id,
            "requester_id": req.requester_id,
            "branch_id": req.branch_conversation_id
        })
        
        return req
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
