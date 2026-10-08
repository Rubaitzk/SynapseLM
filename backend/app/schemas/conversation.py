from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.conversation import SenderType, ExecutionTarget
from app.schemas.user import UserResponse

class ConversationBase(BaseModel):
    title: str
    owner_id: Optional[str] = None
    team_id: Optional[str] = None

class ConversationCreate(ConversationBase):
    ai_provider: Optional[str] = "gemini"
    ai_model: Optional[str] = "gemini-1.5-flash"
    ai_execution_target: Optional[ExecutionTarget] = ExecutionTarget.hosted
    ai_system_instructions: Optional[str] = None
    ai_temperature: Optional[float] = 0.7

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_execution_target: Optional[ExecutionTarget] = None
    ai_system_instructions: Optional[str] = None
    ai_temperature: Optional[float] = None

class ConversationResponse(ConversationBase):
    id: str
    created_at: datetime
    updated_at: datetime
    ai_provider: str
    ai_model: str
    ai_execution_target: ExecutionTarget
    ai_system_instructions: Optional[str] = None
    ai_temperature: float

    class Config:
        from_attributes = True

class ConversationParticipantResponse(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    conversation_id: str
    sender_id: Optional[str] = None
    sender_type: SenderType
    created_at: datetime
    sender: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class PaginatedMessages(BaseModel):
    total: int
    page: int
    size: int
    items: List[MessageResponse]
