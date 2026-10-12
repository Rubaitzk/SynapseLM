import uuid
from datetime import datetime, timezone, timedelta
from app.models.team import Invitation, InvitationStatus

def setup_user(client, prefix="user"):
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    username = f"{prefix}_{uid}"
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    res = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    token = res.json()["access_token"]
    return {
        "email": email,
        "username": username,
        "headers": {"Authorization": f"Bearer {token}"}
    }

def test_unread_count_and_recipient_inbox_filtering(client):
    owner = setup_user(client, "owner")
    recipient = setup_user(client, "recip")

    # Initial unread count should be 0
    count_res = client.get("/api/invitations/unread-count", headers=recipient["headers"])
    assert count_res.status_code == 200
    assert count_res.json()["count"] == 0

    # Owner creates two teams
    t1 = client.post("/api/teams/", json={"name": "Team One"}, headers=owner["headers"]).json()
    t2 = client.post("/api/teams/", json={"name": "Team Two"}, headers=owner["headers"]).json()

    # Invite recipient to Team One
    inv1_res = client.post(
        f"/api/teams/{t1['id']}/invitations",
        json={"invitee_email": recipient["email"], "role": "member"},
        headers=owner["headers"]
    )
    assert inv1_res.status_code == 200
    inv1_id = inv1_res.json()["id"]

    # Invite recipient to Team Two
    inv2_res = client.post(
        f"/api/teams/{t2['id']}/invitations",
        json={"invitee_email": recipient["email"], "role": "admin"},
        headers=owner["headers"]
    )
    assert inv2_res.status_code == 200
    inv2_id = inv2_res.json()["id"]

    # Unread count should now be 2
    count_res = client.get("/api/invitations/unread-count", headers=recipient["headers"])
    assert count_res.json()["count"] == 2

    # Accept inv1
    acc_res = client.post(f"/api/invitations/{inv1_id}/accept", headers=recipient["headers"])
    assert acc_res.status_code == 200

    # Unread count should decrease to 1
    count_res = client.get("/api/invitations/unread-count", headers=recipient["headers"])
    assert count_res.json()["count"] == 1

    # Decline inv2
    dec_res = client.post(f"/api/invitations/{inv2_id}/decline", headers=recipient["headers"])
    assert dec_res.status_code == 200
    assert dec_res.json()["status"] == "rejected"

    # Unread count should decrease to 0
    count_res = client.get("/api/invitations/unread-count", headers=recipient["headers"])
    assert count_res.json()["count"] == 0

    # Verify recipient inbox filters
    pending_list = client.get("/api/invitations/?status=pending", headers=recipient["headers"]).json()
    assert len(pending_list) == 0

    accepted_list = client.get("/api/invitations/?status=accepted", headers=recipient["headers"]).json()
    assert len(accepted_list) == 1
    assert accepted_list[0]["id"] == inv1_id
    assert accepted_list[0]["team"]["name"] == "Team One"

    declined_list = client.get("/api/invitations/?status=declined", headers=recipient["headers"]).json()
    assert len(declined_list) == 1
    assert declined_list[0]["id"] == inv2_id

    all_list = client.get("/api/invitations/?status=all", headers=recipient["headers"]).json()
    assert len(all_list) == 2


def test_sender_dashboard_and_cancellation(client):
    owner = setup_user(client, "dashowner")
    recipient = setup_user(client, "dashrecip")
    outsider = setup_user(client, "outsider")

    # Create team
    team = client.post("/api/teams/", json={"name": "Dashboard Team"}, headers=owner["headers"]).json()
    team_id = team["id"]

    # Non-member cannot access team invitations
    forbidden_res = client.get(f"/api/teams/{team_id}/invitations", headers=outsider["headers"])
    assert forbidden_res.status_code == 403

    # Send invitation
    inv_res = client.post(
        f"/api/teams/{team_id}/invitations",
        json={"invitee_email": recipient["email"], "role": "member"},
        headers=owner["headers"]
    )
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    # Owner views invitations on team dashboard
    team_invs = client.get(f"/api/teams/{team_id}/invitations", headers=owner["headers"]).json()
    assert len(team_invs) == 1
    assert team_invs[0]["id"] == inv_id
    assert team_invs[0]["invitee_email"] == recipient["email"]
    assert team_invs[0]["invitee_name"] == recipient["username"]
    assert team_invs[0]["status"] == "pending"

    # Outsider cannot cancel invitation
    cancel_forbidden = client.post(f"/api/teams/{team_id}/invitations/{inv_id}/cancel", headers=outsider["headers"])
    assert cancel_forbidden.status_code == 403

    # Owner cancels invitation
    cancel_res = client.post(f"/api/teams/{team_id}/invitations/{inv_id}/cancel", headers=owner["headers"])
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Status in sender dashboard filter
    pending_sender = client.get(f"/api/teams/{team_id}/invitations?status=pending", headers=owner["headers"]).json()
    assert len(pending_sender) == 0

    cancelled_sender = client.get(f"/api/teams/{team_id}/invitations?status=cancelled", headers=owner["headers"]).json()
    assert len(cancelled_sender) == 1
    assert cancelled_sender[0]["status"] == "cancelled"

    # Recipient cannot accept cancelled invitation
    cannot_accept = client.post(f"/api/invitations/{inv_id}/accept", headers=recipient["headers"])
    assert cannot_accept.status_code == 400
    assert "cancelled" in cannot_accept.json()["detail"].lower()


def test_authorization_checks(client):
    owner = setup_user(client, "authowner")
    recipient = setup_user(client, "authrecip")
    intruder = setup_user(client, "intruder")

    team = client.post("/api/teams/", json={"name": "Auth Team"}, headers=owner["headers"]).json()
    inv_res = client.post(
        f"/api/teams/{team['id']}/invitations",
        json={"invitee_email": recipient["email"], "role": "member"},
        headers=owner["headers"]
    )
    inv_id = inv_res.json()["id"]

    # Intruder cannot accept recipient's invitation
    bad_accept = client.post(f"/api/invitations/{inv_id}/accept", headers=intruder["headers"])
    assert bad_accept.status_code == 403

    # Intruder cannot decline recipient's invitation
    bad_decline = client.post(f"/api/invitations/{inv_id}/decline", headers=intruder["headers"])
    assert bad_decline.status_code == 403
