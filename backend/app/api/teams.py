from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api import deps
from app.crud import crud_team, crud_user
from app.schemas.team import TeamCreate, TeamResponse, TeamMembershipResponse, InvitationCreate, InvitationResponse
from app.models.team import Role, InvitationStatus
from app.core.realtime import manager

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

@router.get("/{team_id}/invitations", response_model=List[InvitationResponse])
def get_team_invitations(
    team_id: str,
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected, cancelled, expired, or all"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership or membership.role not in [Role.owner, Role.admin]:
        raise HTTPException(status_code=403, detail="Not enough permissions to view team invitations")
    return crud_team.get_team_invitations(db, team_id=team_id, status_filter=status)

@router.post("/{team_id}/invitations", response_model=InvitationResponse)
async def invite_member(
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

    invitation = crud_team.create_invitation(db, invitation=invitation_in, team_id=team_id, inviter_id=current_user.id)

    # Realtime notification to invitee if they are registered
    await manager.broadcast_to_user(user.id, {
        "event": "team.invitation.created",
        "invitation_id": invitation.id,
        "team_id": team_id,
        "team_name": invitation.team.name if invitation.team else None,
        "inviter_name": current_user.username,
        "role": invitation.role.value
    })

    # Realtime notification to team channel
    await manager.broadcast_to_team(team_id, {
        "event": "team.invitation.created",
        "invitation_id": invitation.id,
        "team_id": team_id,
        "invitee_email": invitation.invitee_email,
        "role": invitation.role.value
    })

    return invitation

@router.post("/{team_id}/invitations/{invitation_id}/cancel", response_model=InvitationResponse)
@router.delete("/{team_id}/invitations/{invitation_id}", response_model=InvitationResponse)
async def cancel_team_invitation(
    team_id: str,
    invitation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not membership or membership.role not in [Role.owner, Role.admin]:
        raise HTTPException(status_code=403, detail="Not enough permissions to cancel invitations")

    invitation = crud_team.get_invitation(db, invitation_id=invitation_id)
    if not invitation or invitation.team_id != team_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != InvitationStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot cancel invitation with status: {invitation.status.value}")

    cancelled = crud_team.cancel_invitation(db, invitation=invitation)

    # Notify recipient if registered
    invitee = crud_user.get_user_by_email(db, email=invitation.invitee_email)
    if invitee:
        await manager.broadcast_to_user(invitee.id, {
            "event": "team.invitation.cancelled",
            "invitation_id": invitation.id,
            "team_id": team_id,
            "team_name": invitation.team.name if invitation.team else None
        })

    # Notify team channel
    await manager.broadcast_to_team(team_id, {
        "event": "team.invitation.cancelled",
        "invitation_id": invitation.id,
        "team_id": team_id
    })

    return cancelled

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: str,
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    # Check if current user is owner/admin
    current_membership = crud_team.get_team_membership(db, team_id=team_id, user_id=current_user.id)
    if not current_membership or (current_membership.role not in [Role.owner, Role.admin] and current_user.id != user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions to remove team members")

    # Prevent removing the last owner (unless there's logic for it, keep it simple for now)
    
    membership = crud_team.get_team_membership(db, team_id=team_id, user_id=user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this team")

    # Delete team membership
    db.delete(membership)
    
    # Cascade: remove user from all conversations in this team
    from app.models.conversation import Conversation, ConversationParticipant
    participations = db.query(ConversationParticipant).join(Conversation).filter(
        Conversation.team_id == team_id,
        ConversationParticipant.user_id == user_id
    ).all()
    
    for p in participations:
        db.delete(p)
        
    db.commit()

    # Broadcast participant removal to all affected conversations
    manager = __import__('app.core.realtime', fromlist=['manager']).manager
    for p in participations:
        await manager.broadcast_to_conversation(p.conversation_id, {
            "event": "participant.removed",
            "conversation_id": p.conversation_id,
            "user_id": user_id
        })

    return None
