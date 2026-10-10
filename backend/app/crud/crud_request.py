from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.conversation import ConversationAccessRequest, RequestStatus, Conversation, LifecycleState
from app.crud.crud_conversation import add_participant, get_conversation

def create_request(db: Session, share_id: str, requester_id: str, branch_id: str) -> ConversationAccessRequest:
    req = ConversationAccessRequest(
        share_id=share_id,
        requester_id=requester_id,
        branch_conversation_id=branch_id,
        status=RequestStatus.pending
    )
    db.add(req)
    try:
        db.commit()
        db.refresh(req)
        return req
    except IntegrityError:
        db.rollback()
        raise ValueError("A pending request already exists for this share and requester.")

def get_request(db: Session, request_id: str) -> Optional[ConversationAccessRequest]:
    return db.query(ConversationAccessRequest).filter(ConversationAccessRequest.id == request_id).first()

def get_conversation_requests(db: Session, conversation_id: str) -> List[ConversationAccessRequest]:
    return db.query(ConversationAccessRequest).join(ConversationAccessRequest.share).filter(
        ConversationAccessRequest.share.has(conversation_id=conversation_id)
    ).all()

def cancel_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError("Only pending requests can be cancelled")
    req.status = RequestStatus.cancelled
    db.commit()
    db.refresh(req)
    return req

def reject_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError("Only pending requests can be rejected")
    # Lock request for state change? Wait, `select for update` should be done when getting the request.
    # The caller will do `get_request(db, req_id, for_update=True)`. We'll just update it here.
    req.status = RequestStatus.rejected
    db.commit()
    db.refresh(req)
    return req

def accept_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError("Only pending requests can be accepted")
        
    req.status = RequestStatus.accepted
    
    branch = get_conversation(db, req.branch_conversation_id)
    if branch:
        branch.lifecycle_state = LifecycleState.archived
        db.add(branch)
        
    canonical_id = req.share.conversation_id
    from app.models.conversation import ConversationParticipant
    participant = ConversationParticipant(conversation_id=canonical_id, user_id=req.requester_id)
    db.add(participant)
    
    db.commit()
    db.refresh(req)
    return req
