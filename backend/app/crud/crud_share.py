from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from app.models.conversation import ConversationShare, Conversation
from app.models.user import User

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_share(db: Session, conversation_id: str, creator_id: str, expires_in_seconds: Optional[int] = None) -> tuple[ConversationShare, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    
    expires_at = None
    if expires_in_seconds:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        
    share = ConversationShare(
        conversation_id=conversation_id,
        token_hash=token_hash,
        created_by=creator_id,
        expires_at=expires_at,
        is_active=True
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    
    return share, token

def get_share_by_token(db: Session, token: str) -> Optional[ConversationShare]:
    token_hash = hash_token(token)
    return db.query(ConversationShare).filter(ConversationShare.token_hash == token_hash).first()

def get_share(db: Session, share_id: str) -> Optional[ConversationShare]:
    return db.query(ConversationShare).filter(ConversationShare.id == share_id).first()

def get_conversation_shares(db: Session, conversation_id: str) -> List[ConversationShare]:
    return db.query(ConversationShare).filter(ConversationShare.conversation_id == conversation_id).all()

def revoke_share(db: Session, share: ConversationShare) -> ConversationShare:
    share.is_active = False
    db.add(share)
    db.commit()
    db.refresh(share)
    return share
