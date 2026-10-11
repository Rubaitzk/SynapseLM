import pytest
import uuid
from app.models.conversation import LifecycleState
from app.core.security import create_access_token
from tests.test_v2_domain import create_test_user
from app.crud.crud_conversation import get_conversation

def test_v2_9_sharing_and_preview_flow(client, db_session):
    # Setup Alice (owner) and Bob (collaborator)
    uid = uuid.uuid4().hex[:8]
    alice = create_test_user(db_session, f"alice_{uid}@test.com")
    bob = create_test_user(db_session, f"bob_{uid}@test.com")
    
    t_alice = create_access_token(alice.id)
    t_bob = create_access_token(bob.id)
    h_alice = {"Authorization": f"Bearer {t_alice}"}
    h_bob = {"Authorization": f"Bearer {t_bob}"}

    # 1. Alice creates conversation
    res = client.post("/api/conversations/", headers=h_alice, json={
        "title": "V2.9 Sharing Test",
        "ai_provider": "mock",
        "ai_model": "mock",
        "ai_execution_target": "hosted",
        "ai_temperature": 0.7
    })
    assert res.status_code == 201
    conv = res.json()
    conv_id = conv["id"]
    assert conv["parent_conversation_id"] is None
    assert conv["lifecycle_state"] == "active"

    # 2. Alice creates a share link
    share_res = client.post(f"/api/conversations/{conv_id}/shares", headers=h_alice, json={"expires_in_seconds": 3600})
    assert share_res.status_code == 200
    share_token = share_res.json()["share_token"]
    assert share_token is not None

    # 3. Bob (not yet participant) previews the share
    bob_prev = client.get(f"/api/shares/{share_token}", headers=h_bob)
    assert bob_prev.status_code == 200
    data = bob_prev.json()
    assert data["title"] == "V2.9 Sharing Test"
    assert data["owner_username"] == alice.username
    assert data["is_participant"] is False
    assert data["conversation_id"] is None

    # Alice (owner) previews her own share link
    alice_prev = client.get(f"/api/shares/{share_token}", headers=h_alice)
    assert alice_prev.status_code == 200
    assert alice_prev.json()["is_participant"] is True
    assert alice_prev.json()["conversation_id"] == conv_id

    # 4. Bob creates a branch from the share
    branch_res = client.post(f"/api/shares/{share_token}/branches", headers=h_bob)
    assert branch_res.status_code == 200
    branch_data = branch_res.json()
    branch_id = branch_data["id"]
    assert branch_data["parent_conversation_id"] == conv_id
    assert branch_data["lifecycle_state"] == "active"

    # Branch cannot create a share
    invalid_share = client.post(f"/api/conversations/{branch_id}/shares", headers=h_bob, json={})
    assert invalid_share.status_code == 400
    assert "Cannot create a share for a branch" in invalid_share.json()["detail"]

    # 5. Bob requests access with his branch
    req_res = client.post(f"/api/shares/{share_token}/requests", headers=h_bob, json={"branch_conversation_id": branch_id})
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    # 6. Alice lists pending requests and sees Bob's username
    reqs_res = client.get(f"/api/conversations/{conv_id}/requests", headers=h_alice)
    assert reqs_res.status_code == 200
    reqs = reqs_res.json()
    assert len(reqs) == 1
    assert reqs[0]["id"] == req_id
    assert reqs[0]["requester"]["username"] == bob.username

    # Bob (non-owner) cannot view requests
    forbidden_reqs = client.get(f"/api/conversations/{conv_id}/requests", headers=h_bob)
    assert forbidden_reqs.status_code == 403

    # 7. Alice accepts Bob's request
    acc_res = client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers=h_alice)
    assert acc_res.status_code == 200

    # 8. Check branch is archived and cannot receive new messages
    db_session.expire_all()
    branch_conv = get_conversation(db_session, branch_id)
    assert branch_conv.lifecycle_state == LifecycleState.archived

    post_to_archived = client.post(f"/api/conversations/{branch_id}/messages", headers=h_bob, json={"content": "msg"})
    assert post_to_archived.status_code == 400
    assert "archived" in post_to_archived.json()["detail"]

    # 9. Now Bob previews the share again - is_participant is now True!
    bob_prev_after = client.get(f"/api/shares/{share_token}", headers=h_bob)
    assert bob_prev_after.status_code == 200
    assert bob_prev_after.json()["is_participant"] is True
    assert bob_prev_after.json()["conversation_id"] == conv_id

    # 10. Health check endpoint test
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"
