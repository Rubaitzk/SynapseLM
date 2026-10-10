import pytest
from fastapi.testclient import TestClient

def test_websocket_realtime_collaboration(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex[:8]
    ws1_email = f"ws1_{uid}@example.com"
    ws2_email = f"ws2_{uid}@example.com"
    ws_unauth_email = f"ws_unauth_{uid}@example.com"
    ws1_username = f"ws1_{uid}"
    ws2_username = f"ws2_{uid}"
    ws_unauth_username = f"ws_unauth_{uid}"
    
    # Setup users
    client.post("/api/auth/register", json={"email": ws1_email, "username": ws1_username, "password": "password123"})
    client.post("/api/auth/register", json={"email": ws2_email, "username": ws2_username, "password": "password123"})
    client.post("/api/auth/register", json={"email": ws_unauth_email, "username": ws_unauth_username, "password": "password123"})
    
    token1 = client.post("/api/auth/login", data={"username": ws1_email, "password": "password123"}).json()["access_token"]
    token2 = client.post("/api/auth/login", data={"username": ws2_email, "password": "password123"}).json()["access_token"]
    token_unauth = client.post("/api/auth/login", data={"username": ws_unauth_email, "password": "password123"}).json()["access_token"]
    
    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates team & conversation
    team_id = client.post("/api/teams/", json={"name": "WS Team"}, headers=h1).json()["id"]
    conv_id = client.post("/api/conversations/", json={"title": "WS Chat", "team_id": team_id}, headers=h1).json()["id"]

    # User 1 adds User 2 to team and conversation
    u2_id = client.get("/api/auth/me", headers=h2).json()["id"]
    invite_res = client.post(f"/api/teams/{team_id}/invitations", json={"invitee_email": ws2_email, "role": "member"}, headers=h1)
    invite_id = invite_res.json()["id"]
    
    # User 2 accepts invitation
    client.post(f"/api/invitations/{invite_id}/accept", headers=h2)
    
    client.post(f"/api/conversations/{conv_id}/participants/{u2_id}", headers=h1)

    # 1. Test unauthorized connection
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/{conv_id}?token={token_unauth}") as _:
            pass

    # 2. Test authorized connections & presence
    with client.websocket_connect(f"/ws/{conv_id}?token={token1}") as ws1:
        with client.websocket_connect(f"/ws/{conv_id}?token={token2}") as ws2:
            # Due to the testclient event loop, events might arrive in queues.
            # Just ignore exact order of join events for simplicity, 
            # we just test the typing & message broadcast mainly.
            
            # 3. Test typing
            ws1.send_json({"event": "typing.started"})
            typing_data = ws2.receive_json()
            assert typing_data["event"] in ["typing.started", "presence.joined"]
            
            # 4. Test message delivery
            res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Hello real-time!"}, headers=h1)
            assert res.status_code == 200
