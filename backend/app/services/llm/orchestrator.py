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
from app.services.llm.exceptions import ProviderConfigurationError

SUPPORTED_MODELS = {
    "gemini": ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-3.8-flash-tts"],
    "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "mock": ["mock"]
}

def validate_provider_and_model(provider_name: str, model_name: str):
    provider_name = provider_name.lower()
    if provider_name not in SUPPORTED_MODELS:
        raise ProviderConfigurationError(
            provider=provider_name,
            detail=f"Provider '{provider_name}' is not supported.",
            error_code="unsupported_provider",
            status_code=400
        )
    if model_name not in SUPPORTED_MODELS[provider_name]:
        raise ProviderConfigurationError(
            provider=provider_name,
            detail=f"Model '{model_name}' is not supported for provider '{provider_name}'.",
            error_code="invalid_provider_model_combo",
            status_code=400
        )

def get_provider(db: Session, conversation: Conversation, user_id: str) -> LLMProvider:
    provider_name = conversation.ai_provider.lower()
    from app.core.config import settings
    from app.crud.crud_credential import get_decrypted_credential
    from app.core.encryption import EncryptionError
    
    validate_provider_and_model(provider_name, conversation.ai_model)
    
    if provider_name == "mock":
        return MockProvider()
        
    try:
        api_key = get_decrypted_credential(db, user_id, provider_name)
    except EncryptionError as e:
        raise ProviderConfigurationError(
            provider=provider_name,
            detail=f"Decryption failed for your personal credential: {str(e)}",
            error_code="decryption_failed",
            status_code=400
        )

    if not api_key:
        api_key = settings.LLM_API_KEY
        
    if not api_key:
        raise ProviderConfigurationError(
            provider=provider_name, 
            detail=f"{provider_name.capitalize()} API key is required but not configured.",
            error_code="provider_configuration_missing",
            status_code=400
        )
        
    if provider_name == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider(api_key=api_key, model=conversation.ai_model)
    elif provider_name == "openai":
        from app.services.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=conversation.ai_model)
    else:
        raise ProviderConfigurationError(
            provider=provider_name,
            detail=f"Provider '{provider_name}' is not supported.",
            error_code="unsupported_provider",
            status_code=400
        )

async def generate_assistant_response(db: Session, conversation_id: str, user_id: str) -> Optional[str]:
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
    provider = get_provider(db, conversation, user_id)
    
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
        err_text = str(e)
        prov_key = getattr(provider, 'api_key', None)
        if prov_key and prov_key in err_text:
            err_text = err_text.replace(prov_key, "[REDACTED]")
        print(f"Provider error: {err_text}")
        content = "I'm sorry, I encountered an error while trying to process that."
        await manager.broadcast_to_conversation(conversation_id, {
            "event": "assistant.response.failed",
            "conversation_id": conversation_id,
            "message_id": response_id,
            "error": err_text
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
