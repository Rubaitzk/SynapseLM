from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api import deps
from app.crud import crud_team, crud_user
from app.schemas.team import InvitationResponse, TeamMembershipResponse
from app.models.team import InvitationStatus

router = APIRouter()

@router.get("/", response_model=List[InvitationResponse])
def get_invitations(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    """
    Get all pending invitations for the current user's email.
    """
    return crud_team.get_user_invitations(db, email=current_user.email)

@router.post("/{invitation_id}/accept", response_model=TeamMembershipResponse)
def accept_invitation(
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
        # User is already a member, just mark as accepted
        invitation.status = InvitationStatus.accepted
        db.commit()
        return existing_membership

    return crud_team.accept_invitation(db, invitation=invitation, user_id=current_user.id)

@router.post("/{invitation_id}/reject")
def reject_invitation(
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
    return {"msg": "Invitation rejected"}
