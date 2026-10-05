from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.conversation import SenderType
from app.schemas.user import UserResponse

class ConversationBase(BaseModel):
    title: str
    team_id: str

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: str
    created_at: datetime
    updated_at: datetime

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
