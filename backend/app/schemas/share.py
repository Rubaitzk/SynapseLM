from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ShareCreate(BaseModel):
    expires_in_seconds: Optional[int] = None

class ConversationShareResponse(BaseModel):
    id: str
    share_token: Optional[str] = None
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SharedConversationPreviewResponse(BaseModel):
    title: str
    owner_username: str
    expires_at: Optional[datetime] = None
