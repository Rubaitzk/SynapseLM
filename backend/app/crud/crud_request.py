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

def get_conversation_requests(
    db: Session, 
    conversation_id: str, 
    status: Optional[RequestStatus] = None
) -> List[ConversationAccessRequest]:
    query = db.query(ConversationAccessRequest).join(ConversationAccessRequest.share).filter(
        ConversationAccessRequest.share.has(conversation_id=conversation_id)
    )
    if status is not None:
        query = query.filter(ConversationAccessRequest.status == status)
    return query.order_by(ConversationAccessRequest.created_at.desc()).all()

def get_request_by_branch(db: Session, branch_conversation_id: str) -> Optional[ConversationAccessRequest]:
    return db.query(ConversationAccessRequest).filter(
        ConversationAccessRequest.branch_conversation_id == branch_conversation_id
    ).order_by(ConversationAccessRequest.created_at.desc()).first()

def cancel_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError(f"Only pending requests can be cancelled (current status: {req.status.value})")
    req.status = RequestStatus.cancelled
    db.commit()
    db.refresh(req)
    return req

def reject_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError(f"Only pending requests can be rejected (current status: {req.status.value})")
    req.status = RequestStatus.rejected
    db.commit()
    db.refresh(req)
    return req

def accept_request(db: Session, req: ConversationAccessRequest) -> ConversationAccessRequest:
    if req.status != RequestStatus.pending:
        raise ValueError(f"Only pending requests can be accepted (current status: {req.status.value})")
        
    req.status = RequestStatus.accepted
    
    branch = get_conversation(db, req.branch_conversation_id)
    if branch:
        branch.lifecycle_state = LifecycleState.archived
        db.add(branch)
        
    canonical_id = req.share.conversation_id
    from app.models.conversation import ConversationParticipant
    existing_participant = db.query(ConversationParticipant).filter_by(
        conversation_id=canonical_id, user_id=req.requester_id
    ).first()
    if not existing_participant:
        participant = ConversationParticipant(conversation_id=canonical_id, user_id=req.requester_id)
        db.add(participant)
    
    db.commit()
    db.refresh(req)
    return req
