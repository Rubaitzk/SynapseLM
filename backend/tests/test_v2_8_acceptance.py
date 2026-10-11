import pytest
import uuid
from app.core.config import settings
from cryptography.fernet import Fernet

fernet_test_key = Fernet.generate_key().decode()

async def dummy_validate(provider_name: str, api_key: str):
    pass

def test_e2e_auth_session_restoration(client):
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@test.com"
    pwd = "SecurePassword123!"

    # 1. Unauthenticated request to protected route fails
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # 2. Register
    reg = client.post("/api/auth/register", json={"email": email, "username": f"u_{uid}", "password": pwd})
    assert reg.status_code == 201

    # 3. Login
    login = client.post("/api/auth/login", data={"username": email, "password": pwd})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    # 4. Session restoration (/auth/me with Bearer token)
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email

    # 5. Logout
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

def test_e2e_settings_credential_lifecycle(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", fernet_test_key)
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate)

    uid = uuid.uuid4().hex[:8]
    client.post("/api/auth/register", json={"email": f"{uid}@test.com", "username": f"u_{uid}", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": f"{uid}@test.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # 1. Initial listing: both gemini and openai are unconfigured
    creds = client.get("/api/credentials/", headers=h).json()
    gemini_entry = next(c for c in creds if c["provider_name"] == "gemini")
    openai_entry = next(c for c in creds if c["provider_name"] == "openai")
    assert gemini_entry["is_configured"] is False
    assert openai_entry["is_configured"] is False

    # 2. Add Gemini credential
    res = client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "gemini_key_1"}, headers=h)
    assert res.status_code == 200
    data = res.json()
    assert data["is_configured"] is True
    assert "gemini_key_1" not in str(data)

    # 3. Verify persistence after refresh (GET /api/credentials/)
    creds_after = client.get("/api/credentials/", headers=h).json()
    gemini_after = next(c for c in creds_after if c["provider_name"] == "gemini")
    assert gemini_after["is_configured"] is True
    assert "gemini_key_1" not in str(creds_after)

    # 4. Replace Gemini credential with key_2
    res_replace = client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "gemini_key_2"}, headers=h)
    assert res_replace.status_code == 200
    assert res_replace.json()["is_configured"] is True

    # 5. Delete Gemini credential
    del_res = client.delete("/api/credentials/gemini", headers=h)
    assert del_res.status_code == 200

    # 6. Verify deleted state
    creds_deleted = client.get("/api/credentials/", headers=h).json()
    gemini_del = next(c for c in creds_deleted if c["provider_name"] == "gemini")
    assert gemini_del["is_configured"] is False

def test_e2e_missing_credential_error_contract(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", fernet_test_key)

    uid = uuid.uuid4().hex[:8]
    client.post("/api/auth/register", json={"email": f"{uid}@test.com", "username": f"u_{uid}", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": f"{uid}@test.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Attempt to create/send in gemini conversation without key or system key
    res = client.post("/api/conversations/", headers=h, json={
        "title": "Unconfigured AI Chat",
        "ai_provider": "gemini",
        "ai_model": "gemini-3.6-flash"
    })
    # Must fail with 400 and structured error_code
    assert res.status_code == 400
    err = res.json()
    assert err["error_code"] == "provider_configuration_missing"
    assert "gemini" in err["provider"].lower()

def test_e2e_shared_conversation_sender_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", fernet_test_key)
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate)

    uid = uuid.uuid4().hex[:8]
    # Alice setup
    client.post("/api/auth/register", json={"email": f"alice_{uid}@test.com", "username": f"alice_{uid}", "password": "pw"})
    t_alice = client.post("/api/auth/login", data={"username": f"alice_{uid}@test.com", "password": "pw"}).json()["access_token"]
    h_alice = {"Authorization": f"Bearer {t_alice}"}
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "ALICE_SECRET_KEY"}, headers=h_alice)

    # Bob setup
    client.post("/api/auth/register", json={"email": f"bob_{uid}@test.com", "username": f"bob_{uid}", "password": "pw"})
    t_bob = client.post("/api/auth/login", data={"username": f"bob_{uid}@test.com", "password": "pw"}).json()["access_token"]
    h_bob = {"Authorization": f"Bearer {t_bob}"}
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "BOB_SECRET_KEY"}, headers=h_bob)

    # Alice creates conversation
    conv_resp = client.post("/api/conversations/", headers=h_alice, json={
        "title": "Team AI Session",
        "ai_provider": "gemini",
        "ai_model": "gemini-3.6-flash"
    })
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # Alice shares conversation
    share_res = client.post(f"/api/conversations/{conv_id}/shares", headers=h_alice, json={})
    assert share_res.status_code == 200
    token = share_res.json()["share_token"]

    # Bob previews share
    prev = client.get(f"/api/shares/{token}", headers=h_bob)
    assert prev.status_code == 200
    assert prev.json()["title"] == "Team AI Session"

    # Bob branches and requests access
    branch_res = client.post(f"/api/shares/{token}/branches", headers=h_bob)
    branch_id = branch_res.json()["id"]
    req_res = client.post(f"/api/shares/{token}/requests", headers=h_bob, json={"branch_conversation_id": branch_id})
    req_id = req_res.json()["id"]

    # Alice accepts request
    acc_res = client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers=h_alice)
    assert acc_res.status_code == 200

    # Intercept provider creation to monitor sender credentials
    captured_keys = []
    class MockGemini:
        def __init__(self, api_key, model):
            captured_keys.append(api_key)
        def generate_response(self, *args, **kwargs):
            return "response"

    monkeypatch.setattr("app.services.llm.gemini_provider.GeminiProvider", MockGemini)

    # Bob sends message -> Bob's key is used
    msg_bob = client.post(f"/api/conversations/{conv_id}/messages", headers=h_bob, json={"content": "Bob says hi"})
    assert msg_bob.status_code == 200
    assert "BOB_SECRET_KEY" in captured_keys
    assert "ALICE_SECRET_KEY" not in captured_keys

    # Alice sends message -> Alice's key is used
    captured_keys.clear()
    msg_alice = client.post(f"/api/conversations/{conv_id}/messages", headers=h_alice, json={"content": "Alice replies"})
    assert msg_alice.status_code == 200
    assert "ALICE_SECRET_KEY" in captured_keys
    assert "BOB_SECRET_KEY" not in captured_keys

    # Participant isolation check: Bob cannot view Alice's credentials
    bob_creds = client.get("/api/credentials/", headers=h_bob).json()
    assert "ALICE_SECRET_KEY" not in str(bob_creds)

def test_e2e_openai_backend_support(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", fernet_test_key)
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate)

    uid = uuid.uuid4().hex[:8]
    client.post("/api/auth/register", json={"email": f"{uid}@test.com", "username": f"u_{uid}", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": f"{uid}@test.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Add OpenAI key
    res = client.post("/api/credentials/", json={"provider_name": "openai", "api_key": "sk-test-key"}, headers=h)
    assert res.status_code == 200

    # Create OpenAI conversation
    conv = client.post("/api/conversations/", headers=h, json={
        "title": "GPT-4o Chat",
        "ai_provider": "openai",
        "ai_model": "gpt-4o"
    })
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    # Intercept OpenAI provider
    openai_keys = []
    class MockOpenAI:
        def __init__(self, api_key, model):
            openai_keys.append((api_key, model))
        def generate_response(self, *args, **kwargs):
            return "openai response"

    monkeypatch.setattr("app.services.llm.openai_provider.OpenAIProvider", MockOpenAI)

    # Send message with OpenAI
    msg = client.post(f"/api/conversations/{conv_id}/messages", headers=h, json={"content": "Hello GPT"})
    assert msg.status_code == 200
    assert len(openai_keys) > 0
    assert openai_keys[0] == ("sk-test-key", "gpt-4o")
