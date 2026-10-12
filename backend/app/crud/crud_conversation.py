from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.conversation import Conversation, ConversationParticipant, Message, SenderType, MessageEditHistory
from app.schemas.conversation import ConversationCreate, MessageCreate

def create_conversation(db: Session, conv_in: ConversationCreate, creator_id: str) -> Conversation:
    from app.core.config import settings
    db_conv = Conversation(
        title=conv_in.title, 
        team_id=conv_in.team_id,
        owner_id=None if conv_in.team_id else creator_id,
        ai_provider=conv_in.ai_provider or settings.LLM_PROVIDER,
        ai_model=conv_in.ai_model or settings.LLM_MODEL,
        ai_execution_target=conv_in.ai_execution_target,
        ai_system_instructions=conv_in.ai_system_instructions,
        ai_temperature=conv_in.ai_temperature
    )
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)

    # Automatically add creator as participant
    add_participant(db, conversation_id=db_conv.id, user_id=creator_id)
    return db_conv

def get_conversation(db: Session, conversation_id: str, for_update: bool = False) -> Optional[Conversation]:
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if for_update:
        query = query.with_for_update()
    return query.first()

def update_conversation(db: Session, db_conv: Conversation, conv_in) -> Conversation:
    update_data = conv_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_conv, field, value)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)
    return db_conv

def get_team_conversations(db: Session, team_id: str, user_id: str, root_only: bool = True) -> List[Conversation]:
    # Only return conversations the user is participating in
    query = db.query(Conversation).join(ConversationParticipant).filter(
        Conversation.team_id == team_id,
        ConversationParticipant.user_id == user_id
    )
    if root_only:
        query = query.filter(Conversation.parent_conversation_id.is_(None))
    return query.all()

def get_user_conversations(db: Session, user_id: str, limit: int = 10, root_only: bool = True) -> List[Conversation]:
    query = db.query(Conversation).join(ConversationParticipant).filter(
        ConversationParticipant.user_id == user_id
    )
    if root_only:
        query = query.filter(Conversation.parent_conversation_id.is_(None))
    return query.order_by(Conversation.updated_at.desc()).limit(limit).all()

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
    # 1. Lock the conversation to serialize message inserts and guarantee sequence_id monotonicity per conversation
    conv = get_conversation(db, conversation_id, for_update=True)
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    db_msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=message_in.content
    )
    db.add(db_msg)
    
    from datetime import datetime, timezone
    conv.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_messages(db: Session, conversation_id: str, skip: int = 0, limit: int = 50) -> Tuple[List[Message], int]:
    conv = get_conversation(db, conversation_id)
    if not conv:
        return [], 0
    
    from sqlalchemy import or_, and_
    if conv.parent_conversation_id:
        query = db.query(Message).filter(
            or_(
                Message.conversation_id == conversation_id,
                and_(
                    Message.conversation_id == conv.parent_conversation_id,
                    Message.sequence_id <= conv.snapshot_sequence_id
                )
            )
        )
    else:
        query = db.query(Message).filter(Message.conversation_id == conversation_id)
        
    total = query.count()
    # sequence_id absolute truth ordering
    messages = query.order_by(Message.sequence_id.asc()).offset(skip).limit(limit).all()
    return messages, total

def create_branch(db: Session, parent_id: str, owner_id: str, title: str) -> Conversation:
    # Lock parent to ensure the snapshot_sequence_id is perfectly stable
    parent = get_conversation(db, parent_id, for_update=True)
    if not parent:
        raise ValueError("Parent conversation not found")
        
    if parent.parent_conversation_id is not None:
        raise ValueError("A branch cannot be the parent of another branch (single-level branching invariant violated)")

    max_seq = db.query(func.max(Message.sequence_id)).filter(Message.conversation_id == parent_id).scalar()

    db_branch = Conversation(
        title=title,
        owner_id=owner_id,
        parent_conversation_id=parent.id,
        snapshot_sequence_id=max_seq,
        ai_provider=parent.ai_provider,
        ai_model=parent.ai_model,
        ai_execution_target=parent.ai_execution_target,
        ai_system_instructions=parent.ai_system_instructions,
        ai_temperature=parent.ai_temperature
    )
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    
    # Automatically add owner as participant
    add_participant(db, conversation_id=db_branch.id, user_id=owner_id)
    return db_branch

def get_message(db: Session, message_id: str, for_update: bool = False) -> Optional[Message]:
    query = db.query(Message).filter(Message.id == message_id)
    if for_update:
        query = query.with_for_update()
    return query.first()

def edit_message(
    db: Session,
    message_id: str,
    new_content: str,
    expected_version: int,
    editor_id: str,
    ai_response_content: Optional[str] = None
) -> Tuple[Optional[Message], Optional[str], Optional[Message]]:
    """
    Atomically edits a message if expected_version matches current version.
    Returns (updated_message, error_code, current_message_if_conflict).
    error_code can be 'not_found' or 'conflict'.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    # 1. Row-level lock on the message
    msg = get_message(db, message_id, for_update=True)
    if not msg:
        return None, "not_found", None
        
    # 2. Check optimistic concurrency version
    if msg.version != expected_version:
        return None, "conflict", msg
        
    # 3. Persist history record of the PREVIOUS version
    history = MessageEditHistory(
        message_id=msg.id,
        version=msg.version,
        content=msg.content,
        ai_response_content=ai_response_content,
        editor_id=editor_id,
        edited_at=now
    )
    db.add(history)
    
    # 4. Update the canonical message record
    msg.content = new_content
    msg.version = msg.version + 1
    msg.is_edited = True
    msg.edited_at = now
    msg.edited_by_id = editor_id
    
    # Update conversation's updated_at
    conv = get_conversation(db, msg.conversation_id)
    if conv:
        conv.updated_at = now
        
    db.commit()
    db.refresh(msg)
    return msg, None, None

def get_message_edit_history(db: Session, message_id: str) -> List[MessageEditHistory]:
    return (
        db.query(MessageEditHistory)
        .filter(MessageEditHistory.message_id == message_id)
        .order_by(MessageEditHistory.version.desc())
        .all()
    )

def get_conversation_branches(db: Session, conversation_id: str) -> List[Conversation]:
    conv = get_conversation(db, conversation_id)
    if not conv:
        return []
    root_id = conv.id if conv.parent_conversation_id is None else conv.parent_conversation_id
    root_conv = get_conversation(db, root_id)
    if not root_conv:
        return [conv]
    return (
        db.query(Conversation)
        .filter(
            (Conversation.id == root_id) | (Conversation.parent_conversation_id == root_id)
        )
        .order_by(Conversation.created_at.asc())
        .all()
    )

def create_continuation(
    db: Session,
    conversation_id: str,
    message_id: str,
    new_content: str,
    user_id: str,
    title: Optional[str] = None
) -> Tuple[Conversation, Message]:
    """
    Creates a new conversation continuation branching from immediately before message_id,
    inserting new_content as the continuation prompt.
    """
    parent_conv = get_conversation(db, conversation_id)
    if not parent_conv:
        raise ValueError("Conversation not found")
        
    target_msg = db.query(Message).filter(Message.id == message_id).first()
    if not target_msg:
        raise ValueError("Target message not found")
        
    # Determine root conversation
    root_conv = parent_conv if parent_conv.parent_conversation_id is None else get_conversation(db, parent_conv.parent_conversation_id)
    if not root_conv:
        root_conv = parent_conv

    # Check for recent idempotent branch creation (within last 5 seconds from same user & same message & prompt)
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    recent_threshold = now - timedelta(seconds=5)
    recent_branch = (
        db.query(Conversation)
        .filter(
            Conversation.parent_conversation_id == root_conv.id,
            Conversation.continuation_from_message_id == target_msg.id,
            Conversation.created_at >= recent_threshold
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if recent_branch:
        recent_msg = (
            db.query(Message)
            .filter(
                Message.conversation_id == recent_branch.id,
                Message.sender_id == user_id,
                Message.content == new_content
            )
            .first()
        )
        if recent_msg:
            return recent_branch, recent_msg

    # Determine snapshot sequence ID (highest sequence strictly less than target_msg)
    if target_msg.conversation_id == root_conv.id:
        prior_seq = (
            db.query(func.max(Message.sequence_id))
            .filter(
                Message.conversation_id == root_conv.id,
                Message.sequence_id < target_msg.sequence_id
            )
            .scalar()
        )
        snapshot_seq = prior_seq if prior_seq is not None else 0
    else:
        snapshot_seq = parent_conv.snapshot_sequence_id or 0

    continuation_title = title or root_conv.title
    
    db_branch = Conversation(
        title=continuation_title,
        owner_id=user_id if not parent_conv.team_id else parent_conv.owner_id,
        team_id=parent_conv.team_id,
        parent_conversation_id=root_conv.id,
        snapshot_sequence_id=snapshot_seq,
        continuation_from_message_id=target_msg.id,
        ai_provider=parent_conv.ai_provider,
        ai_model=parent_conv.ai_model,
        ai_execution_target=parent_conv.ai_execution_target,
        ai_system_instructions=parent_conv.ai_system_instructions,
        ai_temperature=parent_conv.ai_temperature
    )
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    
    # Add creator as participant
    add_participant(db, conversation_id=db_branch.id, user_id=user_id)
    
    # If team conversation, also include existing participants
    if parent_conv.team_id:
        existing_participants = get_participants(db, parent_conv.id)
        for p in existing_participants:
            if p.user_id != user_id:
                try:
                    add_participant(db, conversation_id=db_branch.id, user_id=p.user_id)
                except Exception:
                    pass

    # If target_msg was in branch and had intermediate messages in that branch before target_msg:
    if target_msg.conversation_id == parent_conv.id and parent_conv.id != root_conv.id:
        intermediate_msgs = (
            db.query(Message)
            .filter(
                Message.conversation_id == parent_conv.id,
                Message.sequence_id < target_msg.sequence_id
            )
            .order_by(Message.sequence_id.asc())
            .all()
        )
        for im in intermediate_msgs:
            copied = Message(
                conversation_id=db_branch.id,
                sender_id=im.sender_id,
                sender_type=im.sender_type,
                content=im.content
            )
            db.add(copied)
        db.commit()

    # Now create the corrected message in the new branch
    new_msg = create_message(
        db,
        conversation_id=db_branch.id,
        message_in=MessageCreate(content=new_content),
        sender_id=user_id,
        sender_type=SenderType.user
    )
    
    return db_branch, new_msg
