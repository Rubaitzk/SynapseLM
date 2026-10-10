import httpx
from typing import List, Dict
from app.services.llm.provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("Gemini API key is required but not configured.")
        self.api_key = api_key
        # Ensure model has 'models/' prefix if not present (e.g. models/gemini-1.5-flash)
        if not model.startswith("models/") and not model.startswith("tunedModels/"):
            self.model = f"models/{model}"
        else:
            self.model = model
        
    def generate_response(self, system_instruction: str, messages: List[Dict[str, str]], **kwargs) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model}:generateContent?key={self.api_key}"
        
        contents = []
        for m in messages:
            # map 'assistant' to 'model'
            role = "model" if m["role"] == "assistant" else "user"
            
            text = m["content"]
            if role == "user" and "name" in m and m["name"]:
                text = f"{m['name']}: {text}"
                
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
            
        payload = {
            "contents": contents,
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "role": "user",
                "parts": [{"text": system_instruction}]
            }
            
        temperature = kwargs.get('temperature', 0.7)
        payload["generationConfig"] = {
            "temperature": temperature
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=60.0)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API error: {response.status_code} - {response.text}")
                
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Unexpected Gemini API response format: {data}") from e
