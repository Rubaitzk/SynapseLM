import os
from dotenv import load_dotenv
from app.core.config import settings
from app.services.llm.gemini_provider import GeminiProvider
import httpx

def test_gemini():
    print("Testing Gemini configuration...")
    try:
        if not settings.LLM_API_KEY:
            print("API Key not found in settings!")
            return
            
        provider = GeminiProvider(api_key=settings.LLM_API_KEY, model="gemini-3.6-flash")
        
        # Test minimal request
        response = provider.generate_response(
            system_instruction="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hello! Reply with exactly 'TEST_OK'."}]
        )
        
        print(f"Success! Response: {response.strip()}")
        
    except httpx.HTTPError as e:
        print(f"HTTP Error: {type(e).__name__}")
    except RuntimeError as e:
        print(f"Runtime Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected Error: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    test_gemini()
