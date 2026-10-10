from app.services.llm.context import build_system_instruction, build_message_history
from app.services.llm.mock_provider import MockProvider
from app.models.conversation import Conversation
from app.schemas.conversation import MessageCreate
from app.crud import crud_conversation
from app.models.conversation import SenderType

def test_build_system_instruction():
    conv = Conversation(title="AI Strategy")
    instruction = build_system_instruction(conv)
    assert "AI Strategy" in instruction
    assert "SynapseLM" in instruction

def test_mock_provider():
    provider = MockProvider()
    messages = [{"role": "user", "content": "Hello AI", "name": "alice"}]
    response = provider.generate_response(system_instruction="sys", messages=messages)
    assert "[MOCK]" in response
    assert "Hello AI" in response

def test_ai_message_flow(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    email = f"ai_user_{uid}@example.com"
    username = f"ai_user_{uid}"
    # Setup users and team
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    token = client.post("/api/auth/login", data={"username": email, "password": "password123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    
    # Create team and conversation
    team_id = client.post("/api/teams/", json={"name": "AI Team"}, headers=h).json()["id"]
    conv_id = client.post("/api/conversations/", json={"title": "Test AI", "team_id": team_id}, headers=h).json()["id"]
    
    # Send message
    res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Can you hear me?"}, headers=h)
    assert res.status_code == 200
    
    # AI should have responded automatically because LLM_PROVIDER="mock" by default
    # Let's fetch messages
    res_msg = client.get(f"/api/conversations/{conv_id}/messages?page=1&size=10", headers=h)
    data = res_msg.json()
    assert data["total"] >= 2 # 1 user, 1 assistant
    
    # The last message should be from the assistant (mock provider)
    assistant_msg = data["items"][-1]
    assert assistant_msg["sender_type"] == "assistant"
    assert "[MOCK]" in assistant_msg["content"]
    assert "Can you hear me?" in assistant_msg["content"]
