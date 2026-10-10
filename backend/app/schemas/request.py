from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.conversation import RequestStatus

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
    
    model_config = ConfigDict(from_attributes=True)
