import pytest
from app.models.conversation import LifecycleState
from app.crud.crud_conversation import get_conversation

def test_share_lifecycle_and_branches(client, db_session):
    from tests.test_v2_domain import create_test_user
    from app.core.security import create_access_token
    
    import uuid
    owner = create_test_user(db_session, f"owner_{uuid.uuid4()}@test.com")
    recipient = create_test_user(db_session, f"recipient_{uuid.uuid4()}@test.com")
    
    owner_token = create_access_token(owner.id)
    recipient_token = create_access_token(recipient.id)
    
    # 1. Create a conversation
    resp = client.post("/api/conversations/", headers={"Authorization": f"Bearer {owner_token}"}, json={
        "title": "Canonical",
        "ai_provider": "mock",
        "ai_model": "mock",
        "ai_execution_target": "hosted",
        "ai_temperature": 0.7
    })
    assert resp.status_code == 201
    conv_id = resp.json()["id"]
    
    # 2. Create a share
    resp = client.post(f"/api/conversations/{conv_id}/shares", headers={"Authorization": f"Bearer {owner_token}"}, json={})
    assert resp.status_code == 200
    share_token = resp.json()["share_token"]
    assert share_token is not None
    share_id = resp.json()["id"]
    
    # 3. Preview share
    resp = client.get(f"/api/shares/{share_token}", headers={"Authorization": f"Bearer {recipient_token}"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Canonical"
    
    # 4. Create branch
    resp = client.post(f"/api/shares/{share_token}/branches", headers={"Authorization": f"Bearer {recipient_token}"})
    assert resp.status_code == 200
    branch_id = resp.json()["id"]
    assert branch_id != conv_id
    
    # 5. Create request
    resp = client.post(f"/api/shares/{share_token}/requests", headers={"Authorization": f"Bearer {recipient_token}"}, json={"branch_conversation_id": branch_id})
    assert resp.status_code == 200
    req_id = resp.json()["id"]
    
    # 6. Duplicate request fails
    resp = client.post(f"/api/shares/{share_token}/requests", headers={"Authorization": f"Bearer {recipient_token}"}, json={"branch_conversation_id": branch_id})
    assert resp.status_code == 400
    
    # 7. Accept request
    resp = client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    
    # 8. Check branch is archived
    db_session.expire_all()
    branch = get_conversation(db_session, branch_id)
    assert branch.lifecycle_state == LifecycleState.archived
    
    # 9. Verify recipient can fetch messages of canonical
    resp = client.get(f"/api/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {recipient_token}"})
    assert resp.status_code == 200

    # 10. Revoke share
    resp = client.post(f"/api/conversations/{conv_id}/shares/{share_id}/revoke", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 204

    # 11. Share no longer usable for preview
    resp = client.get(f"/api/shares/{share_token}", headers={"Authorization": f"Bearer {recipient_token}"})
    assert resp.status_code == 404

    # 12. Recipient still has access to canonical (independent access)
    resp = client.get(f"/api/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {recipient_token}"})
    assert resp.status_code == 200

def test_archived_branch_writes_fail(client, db_session):
    from tests.test_v2_domain import create_test_user
    from app.core.security import create_access_token
    import uuid
    
    owner = create_test_user(db_session, f"owner_{uuid.uuid4()}@test.com")
    recipient = create_test_user(db_session, f"recipient_{uuid.uuid4()}@test.com")
    
    owner_token = create_access_token(owner.id)
    recipient_token = create_access_token(recipient.id)
    
    # canonical
    resp = client.post("/api/conversations/", headers={"Authorization": f"Bearer {owner_token}"}, json={
        "title": "Canonical",
        "ai_provider": "mock",
        "ai_model": "mock",
        "ai_execution_target": "hosted",
        "ai_temperature": 0.7
    })
    conv_id = resp.json()["id"]
    
    # share
    resp = client.post(f"/api/conversations/{conv_id}/shares", headers={"Authorization": f"Bearer {owner_token}"}, json={})
    share_token = resp.json()["share_token"]
    
    # branch
    resp = client.post(f"/api/shares/{share_token}/branches", headers={"Authorization": f"Bearer {recipient_token}"})
    branch_id = resp.json()["id"]
    
    # request
    resp = client.post(f"/api/shares/{share_token}/requests", headers={"Authorization": f"Bearer {recipient_token}"}, json={"branch_conversation_id": branch_id})
    req_id = resp.json()["id"]
    
    # accept request -> archives branch
    client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers={"Authorization": f"Bearer {owner_token}"})
    
    # writing to branch should fail
    resp = client.post(f"/api/conversations/{branch_id}/messages", headers={"Authorization": f"Bearer {recipient_token}"}, json={"content": "fail"})
    assert resp.status_code == 400
    assert "archived" in resp.json()["detail"]
