def test_invitation_flow(client):
    # Setup owner
    client.post("/api/auth/register", json={"email": "owner@example.com", "username": "owner", "password": "password123"})
    res = client.post("/api/auth/login", data={"username": "owner@example.com", "password": "password123"})
    owner_token = res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Setup invitee
    client.post("/api/auth/register", json={"email": "invitee@example.com", "username": "invitee", "password": "password123"})
    res = client.post("/api/auth/login", data={"username": "invitee@example.com", "password": "password123"})
    invitee_token = res.json()["access_token"]
    invitee_headers = {"Authorization": f"Bearer {invitee_token}"}

    # Owner creates team
    team_res = client.post("/api/teams/", json={"name": "Invite Team"}, headers=owner_headers)
    team_id = team_res.json()["id"]

    # Owner invites invitee
    invite_res = client.post(f"/api/teams/{team_id}/invitations", json={"invitee_email": "invitee@example.com", "role": "member"}, headers=owner_headers)
    assert invite_res.status_code == 200
    invitation_id = invite_res.json()["id"]

    # Prevent duplicate invitations
    dup_res = client.post(f"/api/teams/{team_id}/invitations", json={"invitee_email": "invitee@example.com", "role": "member"}, headers=owner_headers)
    assert dup_res.status_code == 400

    # Invitee lists pending invitations
    list_res = client.get("/api/invitations/", headers=invitee_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Invitee accepts invitation
    accept_res = client.post(f"/api/invitations/{invitation_id}/accept", headers=invitee_headers)
    assert accept_res.status_code == 200

    # Invitee is now a member
    members_res = client.get(f"/api/teams/{team_id}/members", headers=owner_headers)
    assert len(members_res.json()) == 2
