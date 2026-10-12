from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
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
    created = get_invitation(db, db_invitation.id)
    if created:
        _populate_invitee_names(db, [created])
        return created
    return db_invitation

def get_invitation(db: Session, invitation_id: str) -> Optional[Invitation]:
    inv = db.query(Invitation).options(
        joinedload(Invitation.team),
        joinedload(Invitation.inviter)
    ).filter(Invitation.id == invitation_id).first()
    if inv and inv.status == InvitationStatus.pending:
        expires_at = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at.tzinfo is None else inv.expires_at
        if expires_at <= datetime.now(timezone.utc):
            inv.status = InvitationStatus.expired
            db.commit()
            db.refresh(inv)
    return inv

def get_pending_invitation_by_email(db: Session, team_id: str, email: str) -> Optional[Invitation]:
    return db.query(Invitation).filter(
        Invitation.team_id == team_id,
        Invitation.invitee_email == email,
        Invitation.status == InvitationStatus.pending
    ).first()

def _populate_invitee_names(db: Session, invitations: List[Invitation]) -> List[Invitation]:
    if not invitations:
        return invitations
    emails = list({inv.invitee_email for inv in invitations if inv.invitee_email})
    users = db.query(User).filter(User.email.in_(emails)).all()
    user_map = {u.email: u.username for u in users}
    for inv in invitations:
        setattr(inv, "invitee_name", user_map.get(inv.invitee_email))
    return invitations

def get_user_invitations(db: Session, email: str, status_filter: Optional[str] = None) -> List[Invitation]:
    now = datetime.now(timezone.utc)
    # Check and update any expired pending invitations for this email
    pending_list = db.query(Invitation).filter(
        Invitation.invitee_email == email,
        Invitation.status == InvitationStatus.pending
    ).all()
    for inv in pending_list:
        expires_at = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at.tzinfo is None else inv.expires_at
        if expires_at <= now:
            inv.status = InvitationStatus.expired
    if pending_list:
        db.commit()

    query = db.query(Invitation).options(
        joinedload(Invitation.team),
        joinedload(Invitation.inviter)
    ).filter(Invitation.invitee_email == email)

    if status_filter == "pending":
        query = query.filter(Invitation.status == InvitationStatus.pending)
    elif status_filter == "accepted":
        query = query.filter(Invitation.status == InvitationStatus.accepted)
    elif status_filter in ["rejected", "declined"]:
        query = query.filter(Invitation.status == InvitationStatus.rejected)
    elif status_filter == "cancelled":
        query = query.filter(Invitation.status == InvitationStatus.cancelled)
    elif status_filter == "expired":
        query = query.filter(Invitation.status == InvitationStatus.expired)

    invitations = query.order_by(Invitation.created_at.desc()).all()
    return _populate_invitee_names(db, invitations)

def get_unread_invitations_count(db: Session, email: str) -> int:
    now = datetime.now(timezone.utc)
    # Count pending non-expired
    return db.query(Invitation).filter(
        Invitation.invitee_email == email,
        Invitation.status == InvitationStatus.pending,
        Invitation.expires_at > now
    ).count()

def get_team_invitations(db: Session, team_id: str, status_filter: Optional[str] = None) -> List[Invitation]:
    now = datetime.now(timezone.utc)
    # Check and update expired
    pending_list = db.query(Invitation).filter(
        Invitation.team_id == team_id,
        Invitation.status == InvitationStatus.pending
    ).all()
    for inv in pending_list:
        expires_at = inv.expires_at.replace(tzinfo=timezone.utc) if inv.expires_at.tzinfo is None else inv.expires_at
        if expires_at <= now:
            inv.status = InvitationStatus.expired
    if pending_list:
        db.commit()

    query = db.query(Invitation).options(
        joinedload(Invitation.team),
        joinedload(Invitation.inviter)
    ).filter(Invitation.team_id == team_id)

    if status_filter == "pending":
        query = query.filter(Invitation.status == InvitationStatus.pending)
    elif status_filter == "accepted":
        query = query.filter(Invitation.status == InvitationStatus.accepted)
    elif status_filter in ["rejected", "declined"]:
        query = query.filter(Invitation.status == InvitationStatus.rejected)
    elif status_filter == "cancelled":
        query = query.filter(Invitation.status == InvitationStatus.cancelled)
    elif status_filter == "expired":
        query = query.filter(Invitation.status == InvitationStatus.expired)

    invitations = query.order_by(Invitation.created_at.desc()).all()
    return _populate_invitee_names(db, invitations)

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
    db.refresh(invitation)
    return membership

def reject_invitation(db: Session, invitation: Invitation) -> Invitation:
    invitation.status = InvitationStatus.rejected
    db.commit()
    db.refresh(invitation)
    return invitation

def cancel_invitation(db: Session, invitation: Invitation) -> Invitation:
    invitation.status = InvitationStatus.cancelled
    db.commit()
    db.refresh(invitation)
    return invitation
