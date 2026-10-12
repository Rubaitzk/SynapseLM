from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.conversation import SenderType, ExecutionTarget, LifecycleState
from app.schemas.user import UserResponse

class ConversationBase(BaseModel):
    title: str
    owner_id: Optional[str] = None
    team_id: Optional[str] = None

class ConversationCreate(ConversationBase):
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
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
    parent_conversation_id: Optional[str] = None
    snapshot_sequence_id: Optional[int] = None
    continuation_from_message_id: Optional[str] = None
    lifecycle_state: LifecycleState = LifecycleState.active

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
    sequence_id: Optional[int] = None
    sender_id: Optional[str] = None
    sender_type: SenderType
    version: int = 1
    is_edited: bool = False
    edited_at: Optional[datetime] = None
    edited_by_id: Optional[str] = None
    created_at: datetime
    sender: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class MessageEdit(BaseModel):
    content: str
    expected_version: int
    regenerate: Optional[bool] = True

class MessageEditHistoryResponse(BaseModel):
    id: str
    message_id: str
    version: int
    content: str
    ai_response_content: Optional[str] = None
    editor_id: Optional[str] = None
    edited_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class MessageContinue(BaseModel):
    content: str
    title: Optional[str] = None

class MessageEditAndRegenerateResponse(BaseModel):
    action: str # "updated" or "branched"
    conversation_id: str
    root_conversation_id: Optional[str] = None
    message: MessageResponse

class ConversationBranchResponse(BaseModel):
    id: str
    title: str
    parent_conversation_id: Optional[str] = None
    continuation_from_message_id: Optional[str] = None
    snapshot_sequence_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaginatedMessages(BaseModel):
    total: int
    page: int
    size: int
    items: List[MessageResponse]
