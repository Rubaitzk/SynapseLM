from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.team import Team, TeamMembership, Invitation, Role, InvitationStatus
from app.models.user import User
from app.schemas.team import TeamCreate, InvitationCreate

def create_team(db: Session, team: TeamCreate, user_id: str) -> Team:
    db_team = Team(name=team.name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    # Creator becomes the owner
    membership = TeamMembership(team_id=db_team.id, user_id=user_id, role=Role.owner)
    db.add(membership)
    db.commit()
    return db_team

def get_team(db: Session, team_id: str) -> Optional[Team]:
    return db.query(Team).filter(Team.id == team_id).first()

def get_user_teams(db: Session, user_id: str) -> List[Team]:
    memberships = db.query(TeamMembership).filter(TeamMembership.user_id == user_id).all()
    return [m.team for m in memberships]

def get_team_membership(db: Session, team_id: str, user_id: str) -> Optional[TeamMembership]:
    return db.query(TeamMembership).filter(TeamMembership.team_id == team_id, TeamMembership.user_id == user_id).first()

def get_team_members(db: Session, team_id: str) -> List[TeamMembership]:
    return db.query(TeamMembership).filter(TeamMembership.team_id == team_id).all()

def remove_team_member(db: Session, team_id: str, user_id: str):
    membership = get_team_membership(db, team_id, user_id)
    if membership:
        db.delete(membership)
        db.commit()

# Invitations
def create_invitation(db: Session, invitation: InvitationCreate, team_id: str, inviter_id: str) -> Invitation:
    expires = datetime.now(timezone.utc) + timedelta(days=7) # 7 days expiry
    db_invitation = Invitation(
        team_id=team_id,
        inviter_id=inviter_id,
        invitee_email=invitation.invitee_email,
        role=invitation.role,
        expires_at=expires
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

def get_invitation(db: Session, invitation_id: str) -> Optional[Invitation]:
    return db.query(Invitation).filter(Invitation.id == invitation_id).first()

def get_pending_invitation_by_email(db: Session, team_id: str, email: str) -> Optional[Invitation]:
    return db.query(Invitation).filter(
        Invitation.team_id == team_id,
        Invitation.invitee_email == email,
        Invitation.status == InvitationStatus.pending
    ).first()

def get_user_invitations(db: Session, email: str) -> List[Invitation]:
    return db.query(Invitation).filter(
        Invitation.invitee_email == email,
        Invitation.status == InvitationStatus.pending,
        Invitation.expires_at > datetime.now(timezone.utc)
    ).all()

def accept_invitation(db: Session, invitation: Invitation, user_id: str) -> TeamMembership:
    invitation.status = InvitationStatus.accepted
    
    membership = TeamMembership(
        team_id=invitation.team_id,
        user_id=user_id,
        role=invitation.role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership

def reject_invitation(db: Session, invitation: Invitation):
    invitation.status = InvitationStatus.rejected
    db.commit()
