from pydantic import BaseModel
from datetime import datetime

class CredentialCreate(BaseModel):
    provider_name: str
    api_key: str

class CredentialResponse(BaseModel):
    id: str
    provider_name: str
    is_configured: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
