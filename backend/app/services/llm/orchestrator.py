from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.llm.provider import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.context import build_system_instruction, build_message_history
from app.crud import crud_conversation
from app.schemas.conversation import MessageCreate
from app.models.conversation import SenderType

def get_provider() -> LLMProvider:
    if settings.LLM_PROVIDER.lower() == "openai":
        from app.services.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=settings.LLM_API_KEY, model=settings.LLM_MODEL)
    else:
        return MockProvider()

def generate_assistant_response(db: Session, conversation_id: str) -> Optional[str]:
    """
    Orchestrates building the context, calling the provider, and persisting the response.
    Returns the generated content.
    """
    conversation = crud_conversation.get_conversation(db, conversation_id)
    if not conversation:
        return None
        
    # 1. Build context
    system_instruction = build_system_instruction(conversation)
    messages = build_message_history(db, conversation_id)
    
    # 2. Get provider
    provider = get_provider()
    
    # 3. Generate response
    try:
        content = provider.generate_response(system_instruction=system_instruction, messages=messages)
    except Exception as e:
        # In a real app we'd log this, maybe persist an error message
        print(f"Provider error: {e}")
        content = "I'm sorry, I encountered an error while trying to process that."
        
    # 4. Persist response
    message_in = MessageCreate(content=content)
    # The assistant doesn't have a user_id, sender_id=None
    crud_conversation.create_message(
        db=db,
        conversation_id=conversation_id,
        message_in=message_in,
        sender_id=None,
        sender_type=SenderType.assistant
    )
    
    return content
