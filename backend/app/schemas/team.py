from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
from app.models.team import Role, InvitationStatus
from app.schemas.user import UserResponse

# Team Schemas
class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# TeamMembership Schemas
class TeamMembershipResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: Role
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Invitation Schemas
class InvitationCreate(BaseModel):
    invitee_email: EmailStr
    role: Role = Role.member

class InvitationResponse(BaseModel):
    id: str
    team_id: str
    inviter_id: str
    invitee_email: str
    role: Role
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    team: Optional[TeamResponse] = None
    inviter: Optional[UserResponse] = None

    class Config:
        from_attributes = True
