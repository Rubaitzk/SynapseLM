import pytest
from app.core.config import settings
from cryptography.fernet import Fernet

mock_key = Fernet.generate_key().decode()

async def dummy_validate_provider_key(provider_name: str, api_key: str):
    pass

def test_user_cannot_access_other_users_credential(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    
    # User A registers and sets credential
    client.post("/api/auth/register", json={"email": "a@ex.com", "username": "a", "password": "pw"})
    token_a = client.post("/api/auth/login", data={"username": "a@ex.com", "password": "pw"}).json()["access_token"]
    h_a = {"Authorization": f"Bearer {token_a}"}
    
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)
    
    res = client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "user-a-key"}, headers=h_a)
    assert res.status_code == 200
    
    # User B registers
    client.post("/api/auth/register", json={"email": "b@ex.com", "username": "b", "password": "pw"})
    token_b = client.post("/api/auth/login", data={"username": "b@ex.com", "password": "pw"}).json()["access_token"]
    h_b = {"Authorization": f"Bearer {token_b}"}
    
    # User B lists credentials -> gemini should not be configured
    res = client.get("/api/credentials/", headers=h_b)
    assert res.status_code == 200
    data = res.json()
    gemini_cred = next(c for c in data if c["provider_name"] == "gemini")
    assert gemini_cred["is_configured"] is False

def test_credential_responses_never_expose_key(client, monkeypatch):
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)
    client.post("/api/auth/register", json={"email": "c@ex.com", "username": "c", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": "c@ex.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    
    res = client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "super-secret-key"}, headers=h)
    data = res.json()
    assert "super-secret-key" not in str(data)
    assert "encrypted_api_key" not in data
    
    res = client.get("/api/credentials/", headers=h)
    data = res.json()
    assert "super-secret-key" not in str(data)

def test_deleted_credential_is_not_reused(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)
    
    client.post("/api/auth/register", json={"email": "d@ex.com", "username": "d", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": "d@ex.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    
    # Create cred
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "k"}, headers=h)
    # Delete cred
    res = client.delete("/api/credentials/gemini", headers=h)
    assert res.status_code == 200
    
    # Check it's deleted
    res = client.get("/api/credentials/", headers=h)
    gemini_cred = next(c for c in res.json() if c["provider_name"] == "gemini")
    assert gemini_cred["is_configured"] is False

def test_shared_conversation_uses_sender_credential(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "system-key")
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)

    # 1. Register Alice and Bob
    client.post("/api/auth/register", json={"email": "alice_shared@ex.com", "username": "alice_sh", "password": "pw"})
    token_alice = client.post("/api/auth/login", data={"username": "alice_shared@ex.com", "password": "pw"}).json()["access_token"]
    h_alice = {"Authorization": f"Bearer {token_alice}"}

    client.post("/api/auth/register", json={"email": "bob_shared@ex.com", "username": "bob_sh", "password": "pw"})
    token_bob = client.post("/api/auth/login", data={"username": "bob_shared@ex.com", "password": "pw"}).json()["access_token"]
    h_bob = {"Authorization": f"Bearer {token_bob}"}

    # 2. Set distinct personal credentials
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "ALICE_KEY"}, headers=h_alice)
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "BOB_KEY"}, headers=h_bob)

    # 3. Alice creates conversation and share link
    resp = client.post("/api/conversations/", headers=h_alice, json={
        "title": "Shared Chat",
        "ai_provider": "gemini",
        "ai_model": "gemini-3.6-flash",
        "ai_execution_target": "hosted",
        "ai_temperature": 0.7
    })
    conv_id = resp.json()["id"]

    resp = client.post(f"/api/conversations/{conv_id}/shares", headers=h_alice, json={})
    share_token = resp.json()["share_token"]

    # 4. Bob previews share, branches, requests access, Alice accepts
    resp = client.post(f"/api/shares/{share_token}/branches", headers=h_bob)
    branch_id = resp.json()["id"]

    resp = client.post(f"/api/shares/{share_token}/requests", headers=h_bob, json={"branch_conversation_id": branch_id})
    req_id = resp.json()["id"]

    client.post(f"/api/conversations/{conv_id}/requests/{req_id}/accept", headers=h_alice)

    # 5. Intercept Provider initialization to check which key is used
    recorded_keys = []
    class DummyGeminiProvider:
        def __init__(self, api_key, model):
            recorded_keys.append(api_key)
        def generate_response(self, *args, **kwargs):
            return "dummy"

    monkeypatch.setattr("app.services.llm.gemini_provider.GeminiProvider", DummyGeminiProvider)

    # 6. Bob sends a message to Alice's conversation
    # The synchronous get_provider check should capture Bob's key
    resp = client.post(f"/api/conversations/{conv_id}/messages", headers=h_bob, json={"content": "Hi Alice"})
    assert resp.status_code == 200

    # The background task might also run DummyGeminiProvider, but both should use BOB_KEY
    assert "BOB_KEY" in recorded_keys
    assert "ALICE_KEY" not in recorded_keys
    assert "system-key" not in recorded_keys
