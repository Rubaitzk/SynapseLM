import pytest
from fastapi.testclient import TestClient

def test_websocket_request_lifecycle(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex[:8]
    owner_email = f"ws_owner_{uid}@example.com"
    req_email = f"ws_req_{uid}@example.com"
    
    # Setup users
    client.post("/api/auth/register", json={"email": owner_email, "username": f"o_{uid}", "password": "password123"})
    client.post("/api/auth/register", json={"email": req_email, "username": f"r_{uid}", "password": "password123"})
    
    token_owner = client.post("/api/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    token_req = client.post("/api/auth/login", data={"username": req_email, "password": "password123"}).json()["access_token"]
    
    h_owner = {"Authorization": f"Bearer {token_owner}"}
    h_req = {"Authorization": f"Bearer {token_req}"}

    # Owner creates conversation
    conv_id = client.post("/api/conversations/", json={"title": "Shared Chat"}, headers=h_owner).json()["id"]
    
    # Owner creates share
    res_share = client.post(f"/api/conversations/{conv_id}/shares", json={"expires_in_seconds": 3600}, headers=h_owner)
    print(res_share.json())
    share_token = res_share.json()["share_token"]
    
    # Requester creates branch
    branch_id = client.post(f"/api/shares/{share_token}/branches", headers=h_req).json()["id"]
    
    with client.websocket_connect(f"/ws/{conv_id}?token={token_owner}") as ws_owner:
        with client.websocket_connect(f"/ws/{branch_id}?token={token_req}") as ws_req:
            
            # Requester requests access
            req_res = client.post(f"/api/shares/{share_token}/requests", json={"branch_conversation_id": branch_id}, headers=h_req)
            assert req_res.status_code == 200
            req_id = req_res.json()["id"]
            
            # Owner should receive request.created
            event1 = ws_owner.receive_json()
            print("Owner received:", event1)
            tries = 0
            while event1.get("event") not in ["request.created"] and tries < 10:
                event1 = ws_owner.receive_json()
                print("Owner received:", event1)
                tries += 1
                
            assert event1["event"] == "request.created"
            assert event1["request_id"] == req_id
            
            # Owner accepts request
            accept_res = client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers=h_owner)
            print("Accept res:", accept_res.status_code, accept_res.text)
            
            # Owner receives request.accepted and participant.added
            events = []
            for _ in range(2):
                evt = ws_owner.receive_json()
                print("Owner received after accept:", evt)
                events.append(evt)
            event_types = [e["event"] for e in events]
            assert "request.accepted" in event_types
            assert "participant.added" in event_types
            
            # Requester receives request.accepted on branch ws
            event3 = ws_req.receive_json()
            print("Req received:", event3)
            tries = 0
            while event3.get("event") not in ["request.accepted"] and tries < 10:
                event3 = ws_req.receive_json()
                print("Req received:", event3)
                tries += 1
            assert event3["event"] == "request.accepted"
            assert event3["request_id"] == req_id
