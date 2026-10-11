import pytest
import uuid
from app.models.conversation import LifecycleState, RequestStatus
from app.core.security import create_access_token
from tests.test_v2_domain import create_test_user
from app.crud.crud_conversation import get_conversation
from app.crud.crud_request import get_request

def test_v2_11_request_lifecycle_and_state_machine(client, db_session):
    # Setup Alice (owner), Bob (requester 1), Charlie (requester 2)
    uid = uuid.uuid4().hex[:8]
    alice = create_test_user(db_session, f"alice_lc_{uid}@test.com")
    bob = create_test_user(db_session, f"bob_lc_{uid}@test.com")
    charlie = create_test_user(db_session, f"charlie_lc_{uid}@test.com")
    
    t_alice = create_access_token(alice.id)
    t_bob = create_access_token(bob.id)
    t_charlie = create_access_token(charlie.id)
    h_alice = {"Authorization": f"Bearer {t_alice}"}
    h_bob = {"Authorization": f"Bearer {t_bob}"}
    h_charlie = {"Authorization": f"Bearer {t_charlie}"}

    # 1. Alice creates conversation
    conv_res = client.post("/api/conversations/", headers=h_alice, json={
        "title": "Lifecycle Test",
        "ai_provider": "mock",
        "ai_model": "mock",
    })
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 2. Alice creates share link
    share_res = client.post(f"/api/conversations/{conv_id}/shares", headers=h_alice, json={"expires_in_seconds": 3600})
    assert share_res.status_code == 200
    share_token = share_res.json()["share_token"]

    # 3. Bob branches and submits access request
    branch_bob = client.post(f"/api/shares/{share_token}/branches", headers=h_bob).json()
    req_bob = client.post(f"/api/shares/{share_token}/requests", headers=h_bob, json={"branch_conversation_id": branch_bob["id"]}).json()
    bob_req_id = req_bob["id"]

    # 4. Charlie branches and submits access request
    branch_charlie = client.post(f"/api/shares/{share_token}/branches", headers=h_charlie).json()
    req_charlie = client.post(f"/api/shares/{share_token}/requests", headers=h_charlie, json={"branch_conversation_id": branch_charlie["id"]}).json()
    charlie_req_id = req_charlie["id"]

    # 5. Check branch-request endpoint for both requesters
    b_req_res = client.get(f"/api/conversations/{branch_bob['id']}/branch-request", headers=h_bob)
    assert b_req_res.status_code == 200
    assert b_req_res.json()["id"] == bob_req_id
    assert b_req_res.json()["status"] == "pending"

    c_req_res = client.get(f"/api/conversations/{branch_charlie['id']}/branch-request", headers=h_charlie)
    assert c_req_res.status_code == 200
    assert c_req_res.json()["id"] == charlie_req_id
    assert c_req_res.json()["status"] == "pending"

    # 6. Listing requests with and without status filter
    all_reqs = client.get(f"/api/conversations/{conv_id}/requests", headers=h_alice).json()
    assert len(all_reqs) == 2
    pending_reqs = client.get(f"/api/conversations/{conv_id}/requests?status=pending", headers=h_alice).json()
    assert len(pending_reqs) == 2

    # 7. Non-owner cannot decide requests
    unauth_acc = client.post(f"/api/conversations/{conv_id}/requests/{bob_req_id}/accept", headers=h_bob)
    assert unauth_acc.status_code == 403
    unauth_rej = client.post(f"/api/conversations/{conv_id}/requests/{bob_req_id}/reject", headers=h_bob)
    assert unauth_rej.status_code == 403

    # 8. Alice accepts Bob's request
    acc_res = client.post(f"/api/conversations/{conv_id}/requests/{bob_req_id}/accept", headers=h_alice)
    assert acc_res.status_code == 200

    # 9. Duplicate accept on already-accepted request returns 400
    dup_acc = client.post(f"/api/conversations/{conv_id}/requests/{bob_req_id}/accept", headers=h_alice)
    assert dup_acc.status_code == 400
    assert "Only pending requests can be accepted" in dup_acc.json()["detail"]

    # 10. Reject on already-accepted request returns 400
    rej_accepted = client.post(f"/api/conversations/{conv_id}/requests/{bob_req_id}/reject", headers=h_alice)
    assert rej_accepted.status_code == 400
    assert "Only pending requests can be rejected" in rej_accepted.json()["detail"]

    # 11. Alice rejects Charlie's request
    rej_res = client.post(f"/api/conversations/{conv_id}/requests/{charlie_req_id}/reject", headers=h_alice)
    assert rej_res.status_code == 204

    # 12. Duplicate reject on already-rejected request returns 400
    dup_rej = client.post(f"/api/conversations/{conv_id}/requests/{charlie_req_id}/reject", headers=h_alice)
    assert dup_rej.status_code == 400
    assert "Only pending requests can be rejected" in dup_rej.json()["detail"]

    # 13. Accept on already-rejected request returns 400
    acc_rejected = client.post(f"/api/conversations/{conv_id}/requests/{charlie_req_id}/accept", headers=h_alice)
    assert acc_rejected.status_code == 400
    assert "Only pending requests can be accepted" in acc_rejected.json()["detail"]

    # 14. Querying ?status=pending now returns 0 requests
    pending_after = client.get(f"/api/conversations/{conv_id}/requests?status=pending", headers=h_alice).json()
    assert len(pending_after) == 0

    # Querying ?status=accepted returns Bob's request
    accepted_after = client.get(f"/api/conversations/{conv_id}/requests?status=accepted", headers=h_alice).json()
    assert len(accepted_after) == 1
    assert accepted_after[0]["id"] == bob_req_id

    # Querying ?status=rejected returns Charlie's request
    rejected_after = client.get(f"/api/conversations/{conv_id}/requests?status=rejected", headers=h_alice).json()
    assert len(rejected_after) == 1
    assert rejected_after[0]["id"] == charlie_req_id

    # 15. Verify branch-request endpoint reflects the new statuses
    b_check = client.get(f"/api/conversations/{branch_bob['id']}/branch-request", headers=h_bob).json()
    assert b_check["status"] == "accepted"

    c_check = client.get(f"/api/conversations/{branch_charlie['id']}/branch-request", headers=h_charlie).json()
    assert c_check["status"] == "rejected"

def test_v2_11_websocket_decision_notifications(client: pytest.fixture):
    import uuid
    uid = uuid.uuid4().hex[:8]
    owner_email = f"ws_o_{uid}@test.com"
    bob_email = f"ws_b_{uid}@test.com"
    
    client.post("/api/auth/register", json={"email": owner_email, "username": f"own_{uid}", "password": "password123"})
    client.post("/api/auth/register", json={"email": bob_email, "username": f"bob_{uid}", "password": "password123"})
    
    t_owner = client.post("/api/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    t_bob = client.post("/api/auth/login", data={"username": bob_email, "password": "password123"}).json()["access_token"]
    
    h_owner = {"Authorization": f"Bearer {t_owner}"}
    h_bob = {"Authorization": f"Bearer {t_bob}"}

    conv_id = client.post("/api/conversations/", json={"title": "WS Notify Chat"}, headers=h_owner).json()["id"]
    share_token = client.post(f"/api/conversations/{conv_id}/shares", json={"expires_in_seconds": 3600}, headers=h_owner).json()["share_token"]
    branch_id = client.post(f"/api/shares/{share_token}/branches", headers=h_bob).json()["id"]

    with client.websocket_connect(f"/ws/{branch_id}?token={t_bob}") as ws_bob:
        req_id = client.post(f"/api/shares/{share_token}/requests", json={"branch_conversation_id": branch_id}, headers=h_bob).json()["id"]

        # Owner accepts request
        acc_res = client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers=h_owner)
        assert acc_res.status_code == 200

        # Bob receives request.accepted on his branch WebSocket with enriched payload
        event_bob = ws_bob.receive_json()
        tries = 0
        while event_bob.get("event") != "request.accepted" and tries < 10:
            event_bob = ws_bob.receive_json()
            tries += 1

        assert event_bob["event"] == "request.accepted"
        assert event_bob["status"] == "accepted"
        assert event_bob["request_id"] == req_id
        assert event_bob["conversation_title"] == "WS Notify Chat"
        assert event_bob["canonical_conversation_id"] == conv_id
