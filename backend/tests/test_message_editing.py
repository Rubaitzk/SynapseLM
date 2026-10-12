import uuid
import pytest
from app.services.llm.context import build_message_history

def create_user_and_token(client, username_prefix="user"):
    uid = uuid.uuid4().hex[:8]
    email = f"{username_prefix}_{uid}@example.com"
    username = f"{username_prefix}_{uid}"
    password = "password123"
    
    client.post("/api/auth/register", json={"email": email, "username": username, "password": password})
    login_res = client.post("/api/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    user_id = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    return {
        "id": user_id,
        "email": email,
        "username": username,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }

def test_edit_eligible_message_and_increment_version(client):
    u1 = create_user_and_token(client, "alice")
    
    # Create conversation
    res = client.post(
        "/api/conversations/",
        json={"title": "Chat A", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    assert res.status_code == 201
    conv_id = res.json()["id"]
    
    # Send message
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Original message content"},
        headers=u1["headers"]
    )
    assert res.status_code == 200
    msg = res.json()
    msg_id = msg["id"]
    assert msg["content"] == "Original message content"
    assert msg["version"] == 1
    assert msg["is_edited"] is False
    assert msg["edited_at"] is None
    
    # Edit message with expected_version=1
    edit_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Corrected message content", "expected_version": 1},
        headers=u1["headers"]
    )
    assert edit_res.status_code == 200
    updated_msg = edit_res.json()
    assert updated_msg["id"] == msg_id
    assert updated_msg["content"] == "Corrected message content"
    assert updated_msg["version"] == 2
    assert updated_msg["is_edited"] is True
    assert updated_msg["edited_at"] is not None
    assert updated_msg["edited_by_id"] == u1["id"]

def test_record_immutable_edit_history(client):
    u1 = create_user_and_token(client, "alice_hist")
    
    res = client.post(
        "/api/conversations/",
        json={"title": "History Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]
    
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Version 1 content"},
        headers=u1["headers"]
    )
    msg_id = res.json()["id"]
    
    # Before edit, history is empty
    hist_res = client.get(f"/api/conversations/{conv_id}/messages/{msg_id}/history", headers=u1["headers"])
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 0
    
    # First edit: v1 -> v2
    client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Version 2 content", "expected_version": 1},
        headers=u1["headers"]
    )
    
    # History now has v1
    hist_res = client.get(f"/api/conversations/{conv_id}/messages/{msg_id}/history", headers=u1["headers"])
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 1
    assert history[0]["version"] == 1
    assert history[0]["content"] == "Version 1 content"
    assert history[0]["editor_id"] == u1["id"]
    
    # Second edit: v2 -> v3
    client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Version 3 content", "expected_version": 2},
        headers=u1["headers"]
    )
    
    # History now has v2 and v1
    hist_res = client.get(f"/api/conversations/{conv_id}/messages/{msg_id}/history", headers=u1["headers"])
    history = hist_res.json()
    assert len(history) == 2
    assert history[0]["version"] == 2
    assert history[0]["content"] == "Version 2 content"
    assert history[1]["version"] == 1
    assert history[1]["content"] == "Version 1 content"

def test_reject_edits_to_another_users_message(client):
    u1 = create_user_and_token(client, "alice_team")
    u2 = create_user_and_token(client, "bob_team")
    
    # Create team
    team_id = client.post("/api/teams/", json={"name": "Editing Team"}, headers=u1["headers"]).json()["id"]
    
    # Invite and accept bob
    inv_res = client.post(f"/api/teams/{team_id}/invitations", json={"invitee_email": u2["email"], "role": "member"}, headers=u1["headers"])
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]
    accept_res = client.post(f"/api/invitations/{inv_id}/accept", headers=u2["headers"])
    assert accept_res.status_code == 200
    
    # Create team conversation
    res = client.post(
        "/api/conversations/",
        json={"title": "Team Chat", "team_id": team_id, "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]
    
    # Alice adds Bob to conversation
    client.post(f"/api/conversations/{conv_id}/participants/{u2['id']}", headers=u1["headers"])
    
    # Alice sends message
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Alice's message"},
        headers=u1["headers"]
    )
    msg_id = res.json()["id"]
    
    # Bob tries to edit Alice's message -> 403 Forbidden
    edit_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Bob trying to hijack", "expected_version": 1},
        headers=u2["headers"]
    )
    assert edit_res.status_code == 403
    assert "Not authorized" in edit_res.json()["detail"]

def test_reject_unauthorized_conversation_access(client):
    u1 = create_user_and_token(client, "alice_private")
    u2 = create_user_and_token(client, "stranger")
    
    # Alice creates private conversation
    res = client.post(
        "/api/conversations/",
        json={"title": "Private Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]
    
    # Alice sends message
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Secret note"},
        headers=u1["headers"]
    )
    msg_id = res.json()["id"]
    
    # Stranger tries to edit
    edit_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Hacked", "expected_version": 1},
        headers=u2["headers"]
    )
    assert edit_res.status_code == 403
    
    # Stranger tries to view history
    hist_res = client.get(
        f"/api/conversations/{conv_id}/messages/{msg_id}/history",
        headers=u2["headers"]
    )
    assert hist_res.status_code == 403

def test_reject_stale_version_update_optimistic_concurrency(client):
    u1 = create_user_and_token(client, "alice_concur")
    
    res = client.post(
        "/api/conversations/",
        json={"title": "Concurrent Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]
    
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Initial text"},
        headers=u1["headers"]
    )
    msg_id = res.json()["id"]
    
    # Session 1 updates v1 -> v2
    client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Updated by Session 1", "expected_version": 1},
        headers=u1["headers"]
    )
    
    # Session 2 attempts update still thinking it is v1
    stale_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{msg_id}",
        json={"content": "Stale update by Session 2", "expected_version": 1},
        headers=u1["headers"]
    )
    assert stale_res.status_code == 409
    err = stale_res.json()["detail"]
    assert err["current_version"] == 2
    assert err["current_content"] == "Updated by Session 1"
    
    # Message content remains version 2
    msg_check = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=10", headers=u1["headers"]).json()
    user_msg = [m for m in msg_check["items"] if m["id"] == msg_id][0]
    assert user_msg["content"] == "Updated by Session 1"
    assert user_msg["version"] == 2

def test_edit_message_with_existing_replies_preserves_timeline(client):
    u1 = create_user_and_token(client, "alice_replies")
    
    res = client.post(
        "/api/conversations/",
        json={"title": "Multi-turn Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]
    
    # Message 1
    m1_res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Turn 1 question"}, headers=u1["headers"])
    m1_id = m1_res.json()["id"]
    
    # Message 2
    m2_res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Turn 2 question"}, headers=u1["headers"])
    m2_id = m2_res.json()["id"]
    
    # In-place edit of Message 1
    edit_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{m1_id}",
        json={"content": "Turn 1 question (clarified)", "expected_version": 1},
        headers=u1["headers"]
    )
    assert edit_res.status_code == 200
    
    # Fetch messages and verify sequence and relationships
    list_res = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=20", headers=u1["headers"]).json()
    items = list_res["items"]
    
    # First user message has clarified content and is_edited True
    first_msg = [m for m in items if m["id"] == m1_id][0]
    assert first_msg["content"] == "Turn 1 question (clarified)"
    assert first_msg["version"] == 2
    assert first_msg["is_edited"] is True
    
    # Second user message still exists untouched
    second_msg = [m for m in items if m["id"] == m2_id][0]
    assert second_msg["content"] == "Turn 2 question"
    assert second_msg["version"] == 1

def test_edit_and_continue_from_here(client, db_session):
    u1 = create_user_and_token(client, "alice_continue")
    
    res = client.post(
        "/api/conversations/",
        json={"title": "Original Full Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    orig_conv_id = res.json()["id"]
    
    # 1. User Message 1
    m1_res = client.post(f"/api/conversations/{orig_conv_id}/messages", json={"content": "Explain REST APIs."}, headers=u1["headers"])
    m1_id = m1_res.json()["id"]
    
    # 2. User Message 2
    m2_res = client.post(f"/api/conversations/{orig_conv_id}/messages", json={"content": "How are REST APIs different from RPC?"}, headers=u1["headers"])
    m2_id = m2_res.json()["id"]
    
    # User 1 now chooses "Edit and continue from here" on Message 1
    continue_res = client.post(
        f"/api/conversations/{orig_conv_id}/messages/{m1_id}/continue",
        json={"content": "Explain REST APIs and compare them with RPC."},
        headers=u1["headers"]
    )
    assert continue_res.status_code == 200
    data = continue_res.json()
    new_conv = data["conversation"]
    new_msg = data["message"]
    
    assert new_conv["parent_conversation_id"] == orig_conv_id
    assert new_conv["continuation_from_message_id"] == m1_id
    assert new_conv["title"] == "Original Full Chat"  # Title stays clean and stable without (Continued)
    assert new_msg["content"] == "Explain REST APIs and compare them with RPC."
    assert new_msg["conversation_id"] == new_conv["id"]
    
    # Verify branches endpoint returns both root and branch
    branches_res = client.get(f"/api/conversations/{orig_conv_id}/branches", headers=u1["headers"])
    assert branches_res.status_code == 200
    branch_items = branches_res.json()
    assert len(branch_items) == 2
    branch_ids = [b["id"] for b in branch_items]
    assert orig_conv_id in branch_ids
    assert new_conv["id"] in branch_ids

    # Verify GET /api/conversations/ only returns root conversations (no sidebar duplicates)
    user_convs = client.get("/api/conversations/", headers=u1["headers"]).json()
    assert len(user_convs) == 1
    assert user_convs[0]["id"] == orig_conv_id

    # 1. Original conversation timeline is 100% PRESERVED
    orig_list = client.get(f"/api/conversations/{orig_conv_id}/messages?page=1&size=20", headers=u1["headers"]).json()
    orig_contents = [m["content"] for m in orig_list["items"]]
    assert "Explain REST APIs." in orig_contents
    assert "How are REST APIs different from RPC?" in orig_contents
    
    # 2. New continuation conversation contains the corrected message and excludes subsequent messages from original
    new_list = client.get(f"/api/conversations/{new_conv['id']}/messages?page=1&size=20", headers=u1["headers"]).json()
    new_contents = [m["content"] for m in new_list["items"]]
    assert "Explain REST APIs and compare them with RPC." in new_contents
    assert "How are REST APIs different from RPC?" not in new_contents
    
    # 3. AI Context Assembly for the continuation
    history = build_message_history(db_session, new_conv["id"])
    history_contents = [h["content"] for h in history]
    # Contains the new corrected message
    assert any("Explain REST APIs and compare them with RPC." in c for c in history_contents)
    # Does NOT contain subsequent messages from original timeline
    assert not any("How are REST APIs different from RPC?" in c for c in history_contents)

def test_edit_message_regenerates_ai_and_archives_previous_ai_response(client, db_session):
    u1 = create_user_and_token(client, "alice_archive_test")

    res = client.post(
        "/api/conversations/",
        json={"title": "Archive AI Chat", "ai_provider": "mock", "ai_model": "mock"},
        headers=u1["headers"]
    )
    conv_id = res.json()["id"]

    # 1. Post initial prompt (this automatically triggers mock assistant response)
    m1_res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Original user prompt"}, headers=u1["headers"])
    m1_id = m1_res.json()["id"]

    # 2. Verify initial assistant response was generated
    initial_msgs = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=20", headers=u1["headers"]).json()["items"]
    ai_msgs = [m for m in initial_msgs if m["sender_type"] == "assistant"]
    assert len(ai_msgs) == 1
    original_ai_msg = ai_msgs[0]
    original_ai_id = original_ai_msg["id"]
    original_ai_content = original_ai_msg["content"]

    # 3. Edit prompt with regenerate=True
    edit_res = client.patch(
        f"/api/conversations/{conv_id}/messages/{m1_id}",
        json={"content": "Edited user prompt", "expected_version": 1, "regenerate": True},
        headers=u1["headers"]
    )
    assert edit_res.status_code == 200

    # 4. Verify stale AI response was deleted from active conversation
    active_msgs = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=20", headers=u1["headers"]).json()["items"]
    active_ids = [m["id"] for m in active_msgs]
    assert original_ai_id not in active_ids

    # 5. Verify edit history captured the stale AI response content
    hist_res = client.get(f"/api/conversations/{conv_id}/messages/{m1_id}/history", headers=u1["headers"])
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["version"] == 1
    assert history[0]["content"] == "Original user prompt"
    assert history[0]["ai_response_content"] == original_ai_content
