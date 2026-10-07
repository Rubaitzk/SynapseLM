from typing import List, Dict
import openai
from app.services.llm.provider import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        
    def generate_response(self, system_instruction: str, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = [{"role": "system", "content": system_instruction}]
        
        # Convert app format to OpenAI format
        for m in messages:
            msg = {"role": m["role"], "content": m["content"]}
            if "name" in m and m["name"]:
                # Ensure name meets OpenAI's constraints (a-z, A-Z, 0-9, -, _)
                import re
                safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', m["name"])
                if safe_name:
                    msg["name"] = safe_name
            payload.append(msg)
            
        # extract known kwargs
        temperature = kwargs.get('temperature', 0.7)
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            temperature=temperature
        )
        return response.choices[0].message.content
