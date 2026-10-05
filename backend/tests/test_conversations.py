import pytest

def test_conversation_flow(client):
    # Setup users
    client.post("/api/auth/register", json={"email": "u1@example.com", "username": "u1", "password": "password123"})
    client.post("/api/auth/register", json={"email": "u2@example.com", "username": "u2", "password": "password123"})
    
    token1 = client.post("/api/auth/login", data={"username": "u1@example.com", "password": "password123"}).json()["access_token"]
    token2 = client.post("/api/auth/login", data={"username": "u2@example.com", "password": "password123"}).json()["access_token"]
    
    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates team
    team_id = client.post("/api/teams/", json={"name": "Team C"}, headers=h1).json()["id"]

    # User 2 cannot create conversation in Team C since not a member
    res = client.post("/api/conversations/", json={"title": "Unauthorized Conv", "team_id": team_id}, headers=h2)
    assert res.status_code == 403

    # User 1 creates conversation
    res = client.post("/api/conversations/", json={"title": "Design Talk", "team_id": team_id}, headers=h1)
    assert res.status_code == 201
    conv_id = res.json()["id"]

    # User 1 adds User 2 to team (via direct backend or we can just simulate via invitation, but here we can just test conversation participant access directly, wait we need User 2 to be in the team first)
    # Actually, we can test that User 2 cannot access the conversation even if they have the ID.
    res = client.get(f"/api/conversations/{conv_id}", headers=h2)
    assert res.status_code == 403

    # User 1 sends a message
    res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Hello team!"}, headers=h1)
    assert res.status_code == 200
    assert res.json()["content"] == "Hello team!"

    # User 1 gets messages
    res = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=10", headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["items"][0]["content"] == "Hello team!"
    assert data["items"][0]["sender_type"] == "user"
    assert data["items"][1]["sender_type"] == "assistant"

def test_participant_management(client):
    # Setup users
    client.post("/api/auth/register", json={"email": "u3@example.com", "username": "u3", "password": "password123"})
    client.post("/api/auth/register", json={"email": "u4@example.com", "username": "u4", "password": "password123"})
    
    token3 = client.post("/api/auth/login", data={"username": "u3@example.com", "password": "password123"}).json()["access_token"]
    token4 = client.post("/api/auth/login", data={"username": "u4@example.com", "password": "password123"}).json()["access_token"]
    
    h3 = {"Authorization": f"Bearer {token3}"}
    h4 = {"Authorization": f"Bearer {token4}"}

    team_id = client.post("/api/teams/", json={"name": "Team D"}, headers=h3).json()["id"]
    conv_id = client.post("/api/conversations/", json={"title": "Dev Talk", "team_id": team_id}, headers=h3).json()["id"]

    # Add u4 to conversation -> should fail because u4 is not in the team
    u4_info = client.get("/api/auth/me", headers=h4).json()
    u4_id = u4_info["id"]

    res = client.post(f"/api/conversations/{conv_id}/participants/{u4_id}", headers=h3)
    assert res.status_code == 400
    assert "not a member of the team" in res.json()["detail"]
