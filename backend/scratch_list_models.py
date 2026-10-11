import httpx
from app.core.config import settings

def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.LLM_API_KEY}"
    response = httpx.get(url)
    if response.status_code == 200:
        for model in response.json().get('models', []):
            print(model['name'])
    else:
        print(response.text)

if __name__ == "__main__":
    list_models()
