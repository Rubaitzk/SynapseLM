import uuid
_UID = uuid.uuid4().hex[:8]

def test_create_team(client):
    email = f"teamuser_{_UID}@example.com"
    username = f"teamuser_{_UID}"
    # Register and login user 1
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    res = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create team
    res = client.post("/api/teams/", json={"name": "Alpha Team"}, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alpha Team"
    team_id = data["id"]

    # Verify membership
    res = client.get(f"/api/teams/{team_id}/members", headers=headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"

def test_team_visibility(client):
    email1 = f"user1_{_UID}@example.com"
    username1 = f"user1_{_UID}"
    email2 = f"user2_{_UID}@example.com"
    username2 = f"user2_{_UID}"
    
    # User 1 creates team
    client.post("/api/auth/register", json={"email": email1, "username": username1, "password": "password123"})
    res1 = client.post("/api/auth/login", data={"username": email1, "password": "password123"})
    token1 = res1.json()["access_token"]
    
    team_res = client.post("/api/teams/", json={"name": "Secret Team"}, headers={"Authorization": f"Bearer {token1}"})
    team_id = team_res.json()["id"]

    # User 2 tries to access team
    client.post("/api/auth/register", json={"email": email2, "username": username2, "password": "password123"})
    res2 = client.post("/api/auth/login", data={"username": email2, "password": "password123"})
    token2 = res2.json()["access_token"]

    res = client.get(f"/api/teams/{team_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403
