from typing import List, Dict
from app.services.llm.provider import LLMProvider

class MockProvider(LLMProvider):
    def generate_response(self, system_instruction: str, messages: List[Dict[str, str]], **kwargs) -> str:
        # Simply return a mock response
        last_message = messages[-1]["content"] if messages else ""
        return f"[MOCK] I see you said: '{last_message}'. This is a simulated response (temp={kwargs.get('temperature')})."
