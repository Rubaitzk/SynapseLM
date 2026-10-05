from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.conversation import Conversation, ConversationParticipant, Message, SenderType
from app.schemas.conversation import ConversationCreate, MessageCreate

def create_conversation(db: Session, conv_in: ConversationCreate, creator_id: str) -> Conversation:
    db_conv = Conversation(title=conv_in.title, team_id=conv_in.team_id)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)

    # Automatically add creator as participant
    add_participant(db, conversation_id=db_conv.id, user_id=creator_id)
    return db_conv

def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def get_team_conversations(db: Session, team_id: str, user_id: str) -> List[Conversation]:
    # Only return conversations the user is participating in
    return db.query(Conversation).join(ConversationParticipant).filter(
        Conversation.team_id == team_id,
        ConversationParticipant.user_id == user_id
    ).all()

def delete_conversation(db: Session, conversation_id: str):
    conv = get_conversation(db, conversation_id)
    if conv:
        db.delete(conv)
        db.commit()

# Participants
def add_participant(db: Session, conversation_id: str, user_id: str) -> ConversationParticipant:
    participant = ConversationParticipant(conversation_id=conversation_id, user_id=user_id)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant

def get_participant(db: Session, conversation_id: str, user_id: str) -> Optional[ConversationParticipant]:
    return db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user_id
    ).first()

def get_participants(db: Session, conversation_id: str) -> List[ConversationParticipant]:
    return db.query(ConversationParticipant).filter(ConversationParticipant.conversation_id == conversation_id).all()

def remove_participant(db: Session, conversation_id: str, user_id: str):
    participant = get_participant(db, conversation_id, user_id)
    if participant:
        db.delete(participant)
        db.commit()

# Messages
def create_message(db: Session, conversation_id: str, message_in: MessageCreate, sender_id: str, sender_type: SenderType = SenderType.user) -> Message:
    db_msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=message_in.content
    )
    db.add(db_msg)
    
    # Update conversation updated_at
    conv = get_conversation(db, conversation_id)
    if conv:
        from datetime import datetime, timezone
        conv.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_messages(db: Session, conversation_id: str, skip: int = 0, limit: int = 50) -> Tuple[List[Message], int]:
    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    total = query.count()
    # ordering is configured in the relationship and model, but we explicit order here
    messages = query.order_by(Message.created_at.asc()).offset(skip).limit(limit).all()
    return messages, total
