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
    assert "BOB_KEY" in recorded_keys
    assert "ALICE_KEY" not in recorded_keys
    assert "system-key" not in recorded_keys

    # 7. Alice sends a message to the same conversation -> uses ALICE_KEY
    recorded_keys.clear()
    resp_alice = client.post(f"/api/conversations/{conv_id}/messages", headers=h_alice, json={"content": "Welcome Bob"})
    assert resp_alice.status_code == 200
    assert "ALICE_KEY" in recorded_keys
    assert "BOB_KEY" not in recorded_keys
    assert "system-key" not in recorded_keys

def test_credential_replacement_and_isolation(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)

    # User 1 registers and adds key1
    client.post("/api/auth/register", json={"email": "u1@ex.com", "username": "u1", "password": "pw"})
    t1 = client.post("/api/auth/login", data={"username": "u1@ex.com", "password": "pw"}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "KEY_V1"}, headers=h1)

    # User 1 replaces key with key2
    res = client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "KEY_V2"}, headers=h1)
    assert res.status_code == 200

    # User 2 registers
    client.post("/api/auth/register", json={"email": "u2@ex.com", "username": "u2", "password": "pw"})
    t2 = client.post("/api/auth/login", data={"username": "u2@ex.com", "password": "pw"}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    # User 2 attempts to delete gemini credential -> should return 404 because user 2 has no credential
    del_res = client.delete("/api/credentials/gemini", headers=h2)
    assert del_res.status_code == 404

    # User 1's credential must remain intact and configured
    u1_creds = client.get("/api/credentials/", headers=h1).json()
    u1_gemini = next(c for c in u1_creds if c["provider_name"] == "gemini")
    assert u1_gemini["is_configured"] is True

def test_decryption_failure_halts_provider_initialization(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "LLM_API_KEY", "system-key")
    monkeypatch.setattr("app.api.endpoints.credentials.validate_provider_key", dummy_validate_provider_key)
    monkeypatch.setattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', mock_key)

    # Register
    client.post("/api/auth/register", json={"email": "fail@ex.com", "username": "fail", "password": "pw"})
    token = client.post("/api/auth/login", data={"username": "fail@ex.com", "password": "pw"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # Set valid credential
    client.post("/api/credentials/", json={"provider_name": "gemini", "api_key": "VALID_KEY"}, headers=h)

    # Tamper with the ciphertext in DB
    from app.models.credential import UserCredential
    from app.models.user import User
    
    user = db_session.query(User).filter_by(email="fail@ex.com").first()
    cred = db_session.query(UserCredential).filter_by(user_id=user.id).first()
    # Fernet ciphertext must start with gAAAAA, replace some characters
    cred.encrypted_api_key = cred.encrypted_api_key[:-5] + "XXXXX"
    db_session.commit()

    # Attempt to use it
    resp = client.post("/api/conversations/", headers=h, json={
        "title": "Should Fail",
        "ai_provider": "gemini",
        "ai_model": "gemini-3.6-flash",
        "ai_execution_target": "hosted",
        "ai_temperature": 0.7
    })
    
    # Should get a 400 error because decryption fails, not fallback to system key
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "decryption_failed"
