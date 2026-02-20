import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")


def generate_response(prompt: str):
    url = f"{API_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a compliance legal assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"LLM API Error: {response.text}")
            return f"[ERROR] The AI could not generate a response because of an API issue (Status {response.status_code}). Please check your API key and credits."
            
    except Exception as e:
        print(f"LLM Connection Error: {e}")
        return f"[ERROR] Connection to the AI service failed. Detailed error: {str(e)}"
