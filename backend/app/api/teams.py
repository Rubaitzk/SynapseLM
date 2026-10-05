from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api import deps
from app.crud import crud_team, crud_user
from app.schemas.team import TeamCreate, TeamResponse, TeamMembershipResponse, InvitationCreate, InvitationResponse
from app.models.team import Role

router = APIRouter()

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    team = crud_team.create_team(db, team=team_in, user_id=current_user.id)
    return team

@router.get("/", response_model=List[TeamResponse])
def get_teams(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    return crud_team.get_user_teams(db, user_id=current_user.id)

@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return membership.team

@router.get("/{team_id}/members", response_model=List[TeamMembershipResponse])
def get_team_members(
    team_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return crud_team.get_team_members(db, team_id=team_id)

from app.crud import crud_conversation
from app.schemas.conversation import ConversationResponse

@router.get("/{team_id}/conversations", response_model=List[ConversationResponse])
def get_team_conversations(
    team_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return crud_conversation.get_team_conversations(db, team_id=team_id, user_id=current_user.id)

@router.post("/{team_id}/invitations", response_model=InvitationResponse)
def invite_member(
    team_id: str,
    invitation_in: InvitationCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership or membership.role not in [Role.owner, Role.admin]:
        raise HTTPException(status_code=403, detail="Not enough permissions to invite members")

    # check if user is already a member
    user = crud_user.get_user_by_email(db, email=invitation_in.invitee_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. They must register an account first.")
        
    existing_membership = crud_team.get_team_membership(db, team_id=team_id, user_id=user.id)
    if existing_membership:
        raise HTTPException(status_code=400, detail="User is already a member of this team")

    # check for duplicate pending invitation
    existing_invite = crud_team.get_pending_invitation_by_email(db, team_id=team_id, email=invitation_in.invitee_email)
    if existing_invite:
        expires_at = existing_invite.expires_at.replace(tzinfo=timezone.utc) if existing_invite.expires_at.tzinfo is None else existing_invite.expires_at
        if expires_at > datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="A pending invitation already exists for this email")

    return crud_team.create_invitation(db, invitation=invitation_in, team_id=team_id, inviter_id=current_user.id)
