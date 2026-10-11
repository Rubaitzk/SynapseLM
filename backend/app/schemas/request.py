from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.conversation import RequestStatus
from app.schemas.user import UserResponse

class AccessRequestCreate(BaseModel):
    branch_conversation_id: str

class AccessRequestResponse(BaseModel):
    id: str
    share_id: str
    requester_id: str
    branch_conversation_id: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    requester: Optional[UserResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
