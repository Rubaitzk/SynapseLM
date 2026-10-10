import pytest
import uuid
from app.core.config import settings

def get_auth_headers(client):
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@example.com"
    client.post("/api/auth/register", json={"email": email, "username": f"user_{uid}", "password": "password123"})
    token = client.post("/api/auth/login", data={"username": email, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_conversation_invalid_provider(client):
    h = get_auth_headers(client)
    res = client.post("/api/conversations/", json={
        "title": "Invalid Provider Test",
        "ai_provider": "anthropic",
        "ai_model": "claude-3-opus-20240229"
    }, headers=h)
    
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "unsupported_provider"
    assert data["provider"] == "anthropic"

def test_create_conversation_invalid_model_combo(client):
    h = get_auth_headers(client)
    res = client.post("/api/conversations/", json={
        "title": "Invalid Model Test",
        "ai_provider": "gemini",
        "ai_model": "gpt-4o"
    }, headers=h)
    
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "invalid_provider_model_combo"
    assert data["provider"] == "gemini"

def test_create_conversation_missing_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    
    h = get_auth_headers(client)
    res = client.post("/api/conversations/", json={
        "title": "Missing Creds Test",
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash"
    }, headers=h)
    
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "provider_configuration_missing"
    assert data["provider"] == "gemini"

def test_create_conversation_explicit_selection_success(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-key")
    h = get_auth_headers(client)
    res = client.post("/api/conversations/", json={
        "title": "Valid Combo Test",
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash"
    }, headers=h)
    
    assert res.status_code == 201
    data = res.json()
    assert data["ai_provider"] == "gemini"
    assert data["ai_model"] == "gemini-1.5-flash"

def test_send_message_missing_credentials(client, monkeypatch):
    # First, create with a valid fake key
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-key")
    h = get_auth_headers(client)
    conv_id = client.post("/api/conversations/", json={
        "title": "Valid Combo Test",
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash"
    }, headers=h).json()["id"]

    # Now, simulate the key being wiped or unconfigured before the message is sent
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    
    res = client.post(f"/api/conversations/{conv_id}/messages", json={
        "content": "Hello?"
    }, headers=h)
    
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "provider_configuration_missing"
