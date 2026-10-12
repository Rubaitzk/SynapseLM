from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api import deps
from app.crud import crud_team, crud_user
from app.schemas.team import InvitationResponse, TeamMembershipResponse, UnreadInvitationsCount
from app.models.team import InvitationStatus
from app.core.realtime import manager

router = APIRouter()

@router.get("/", response_model=List[InvitationResponse])
def get_invitations(
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected, cancelled, expired, or all"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    """
    Get invitations for the current user's email with optional status filtering.
    """
    return crud_team.get_user_invitations(db, email=current_user.email, status_filter=status)

@router.get("/unread-count", response_model=UnreadInvitationsCount)
def get_unread_count(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    """
    Get unread pending invitations count for current user badge.
    """
    count = crud_team.get_unread_invitations_count(db, email=current_user.email)
    return {"count": count}

@router.post("/{invitation_id}/accept", response_model=TeamMembershipResponse)
async def accept_invitation(
    invitation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    invitation = crud_team.get_invitation(db, invitation_id=invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if invitation.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to accept this invitation")
        
    if invitation.status != InvitationStatus.pending:
        raise HTTPException(status_code=400, detail=f"Invitation is already {invitation.status.value}")
        
    expires_at = invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at
    if expires_at < datetime.now(timezone.utc):
        invitation.status = InvitationStatus.expired
        db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # check if user is already a member
    existing_membership = crud_team.get_team_membership(db, team_id=invitation.team_id, user_id=current_user.id)
    if existing_membership:
        invitation.status = InvitationStatus.accepted
        db.commit()
        membership = existing_membership
    else:
        membership = crud_team.accept_invitation(db, invitation=invitation, user_id=current_user.id)

    # Realtime notifications after commit
    await manager.broadcast_to_team(invitation.team_id, {
        "event": "team.invitation.accepted",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id,
        "user_id": current_user.id,
        "user_name": current_user.username
    })
    await manager.broadcast_to_team(invitation.team_id, {
        "event": "team.membership.created",
        "team_id": invitation.team_id,
        "user_id": current_user.id,
        "user_name": current_user.username,
        "role": invitation.role.value
    })
    await manager.broadcast_to_user(invitation.inviter_id, {
        "event": "team.invitation.accepted",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id,
        "user_id": current_user.id,
        "user_name": current_user.username
    })
    await manager.broadcast_to_user(current_user.id, {
        "event": "team.invitation.accepted",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id
    })

    return membership

@router.post("/{invitation_id}/reject", response_model=InvitationResponse)
@router.post("/{invitation_id}/decline", response_model=InvitationResponse)
async def reject_invitation(
    invitation_id: str,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    invitation = crud_team.get_invitation(db, invitation_id=invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
        
    if invitation.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to reject this invitation")
        
    if invitation.status != InvitationStatus.pending:
        raise HTTPException(status_code=400, detail=f"Invitation is already {invitation.status.value}")

    crud_team.reject_invitation(db, invitation=invitation)

    # Realtime notifications after commit
    await manager.broadcast_to_user(invitation.inviter_id, {
        "event": "team.invitation.declined",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id,
        "user_id": current_user.id,
        "user_name": current_user.username
    })
    await manager.broadcast_to_team(invitation.team_id, {
        "event": "team.invitation.declined",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id,
        "user_id": current_user.id,
        "user_name": current_user.username
    })
    await manager.broadcast_to_user(current_user.id, {
        "event": "team.invitation.declined",
        "invitation_id": invitation.id,
        "team_id": invitation.team_id
    })

    return invitation
