from typing import Optional
from sqlalchemy.orm import Session
from app.services.llm.provider import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.context import build_system_instruction, build_message_history
from app.crud import crud_conversation
from app.models.conversation import SenderType, Conversation
from app.schemas.conversation import MessageCreate, MessageResponse
import asyncio
from app.core.realtime import manager
import uuid

def get_provider(conversation: Conversation) -> LLMProvider:
    provider_name = conversation.ai_provider.lower()
    from app.core.config import settings
    
    if provider_name == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider
        if not settings.LLM_API_KEY:
            raise ValueError("Gemini API key is required but not configured.")
        return GeminiProvider(api_key=settings.LLM_API_KEY, model=conversation.ai_model)
    elif provider_name == "openai":
        from app.services.llm.openai_provider import OpenAIProvider
        if not settings.LLM_API_KEY:
            raise ValueError("OpenAI API key is required but not configured.")
        return OpenAIProvider(api_key=settings.LLM_API_KEY, model=conversation.ai_model)
    else:
        return MockProvider()

async def generate_assistant_response(db: Session, conversation_id: str) -> Optional[str]:
    """
    Orchestrates building the context, calling the provider, and persisting the response.
    Returns the generated content.
    """
    conversation = crud_conversation.get_conversation(db, conversation_id)
    if not conversation:
        return None
        
    # 1. Build context
    system_instruction = build_system_instruction(conversation)
    # prepend conversation AI system instruction if provided
    if conversation.ai_system_instructions:
        system_instruction = f"{conversation.ai_system_instructions}\n\n{system_instruction}"
        
    messages = build_message_history(db, conversation_id)
    
    # 2. Get provider
    provider = get_provider(conversation)
    
    response_id = str(uuid.uuid4())
    
    await manager.broadcast_to_conversation(conversation_id, {
        "event": "assistant.response.started",
        "conversation_id": conversation_id,
        "message_id": response_id
    })
    
    # 3. Generate response
    content = ""
    try:
        # Run sync provider in thread pool to not block event loop
        content = await asyncio.to_thread(
            provider.generate_response, 
            system_instruction, 
            messages,
            temperature=conversation.ai_temperature
        )
        
        # Fake streaming it out
        words = content.split(" ")
        for i, word in enumerate(words):
            await manager.broadcast_to_conversation(conversation_id, {
                "event": "assistant.response.delta",
                "conversation_id": conversation_id,
                "message_id": response_id,
                "content": word + (" " if i < len(words) - 1 else "")
            })
            await asyncio.sleep(0.05)
            
    except Exception as e:
        print(f"Provider error: {e}")
        content = "I'm sorry, I encountered an error while trying to process that."
        await manager.broadcast_to_conversation(conversation_id, {
            "event": "assistant.response.failed",
            "conversation_id": conversation_id,
            "message_id": response_id,
            "error": str(e)
        })
        return None
        
    # 4. Persist response
    message_in = MessageCreate(content=content)
    msg = crud_conversation.create_message(
        db=db,
        conversation_id=conversation_id,
        message_in=message_in,
        sender_id=None,
        sender_type=SenderType.assistant
    )
    
    message_data = MessageResponse.model_validate(msg).model_dump(mode='json')
    
    await manager.broadcast_to_conversation(conversation_id, {
        "event": "assistant.response.completed",
        "conversation_id": conversation_id,
        "message_id": response_id,
        "message": message_data
    })
    
    return content
