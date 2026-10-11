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
