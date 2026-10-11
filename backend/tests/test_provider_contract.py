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
        "ai_model": "gemini-3.6-flash"
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
        "ai_model": "gemini-3.6-flash"
    }, headers=h)
    
    assert res.status_code == 201
    data = res.json()
    assert data["ai_provider"] == "gemini"
    assert data["ai_model"] == "gemini-3.6-flash"

def test_send_message_missing_credentials(client, monkeypatch):
    # First, create with a valid fake key
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-key")
    h = get_auth_headers(client)
    res = client.post('/api/conversations/', json={'title': 'Valid Combo Test', 'ai_provider': 'gemini', 'ai_model': 'gemini-3.6-flash'}, headers=h)
    assert res.status_code == 201, res.text
    conv_id = res.json()['id']

    # Now, simulate the key being wiped or unconfigured before the message is sent
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    
    res = client.post(f"/api/conversations/{conv_id}/messages", json={
        "content": "Hello?"
    }, headers=h)
    
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "provider_configuration_missing"

def test_create_conversation_default_model_resolution(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_MODEL", "gemini-3.6-flash")
    
    h = get_auth_headers(client)
    res = client.post("/api/conversations/", json={
        "title": "Default Model Test"
    }, headers=h)
    
    assert res.status_code == 201
    data = res.json()
    assert data["ai_provider"] == "gemini"
    assert data["ai_model"] == "gemini-3.6-flash"

def test_send_message_obsolete_model_upgrade(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-key")
    h = get_auth_headers(client)
    
    res = client.post("/api/conversations/", json={
        "title": "Obsolete Model Test",
        "ai_provider": "gemini",
        "ai_model": "gemini-3.6-flash" # Create with valid model first
    }, headers=h)
    assert res.status_code == 201, res.text
    conv_id = res.json()["id"]
    
    # We mock get_conversation to return a conversation with an obsolete model
    import app.crud.crud_conversation as crud_conv
    original_get = crud_conv.get_conversation
    
    def mock_get_conversation(db, cid, **kwargs):
        conv = original_get(db, cid, **kwargs)
        if conv and cid == conv_id:
            conv.ai_model = "gemini-1.5-flash"
        return conv
        
    monkeypatch.setattr(crud_conv, "get_conversation", mock_get_conversation)
    
    # Now send a message, it should succeed by auto-upgrading in memory
    res_msg = client.post(f"/api/conversations/{conv_id}/messages", json={
        "content": "Hello obsolete model"
    }, headers=h)
    
    assert res_msg.status_code == 200, res_msg.text
