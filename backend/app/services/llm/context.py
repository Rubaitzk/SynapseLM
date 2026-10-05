from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.crud import crud_conversation
from app.models.conversation import Conversation, SenderType
from app.models.user import User

def build_system_instruction(conversation: Conversation) -> str:
    """
    Builds the system instruction / prompt for the AI based on the conversation context.
    """
    return (
        f"You are an AI assistant in a collaborative workspace named SynapseLM. "
        f"You are participating in a conversation titled '{conversation.title}'. "
        f"Multiple users might be talking to you. Pay attention to who is speaking."
    )

def build_message_history(db: Session, conversation_id: str, limit: int = 20) -> List[Dict[str, str]]:
    """
    Retrieves the recent message history and formats it for the AI provider.
    """
    # Get last N messages (reverse order for query, then reverse back to chronological)
    # Actually our crud gets oldest first, so we just get skip=max(0, total-limit)
    _, total = crud_conversation.get_messages(db, conversation_id, skip=0, limit=1) # just to get total
    
    skip = max(0, total - limit)
    messages, _ = crud_conversation.get_messages(db, conversation_id, skip=skip, limit=limit)
    
    history = []
    for msg in messages:
        role = "assistant" if msg.sender_type in [SenderType.assistant, SenderType.system] else "user"
        formatted_msg = {
            "role": role,
            "content": msg.content
        }
        
        # Add the username as 'name' if available to help AI distinguish users
        if msg.sender:
            formatted_msg["name"] = msg.sender.username
            # Also prepend name to content as fallback for models that ignore 'name' field
            if role == "user":
                formatted_msg["content"] = f"{msg.sender.username}: {msg.content}"
                
        history.append(formatted_msg)
        
    return history
