# app/utils/llm_client.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# NOTE: The env var is XAI_API_KEY (matches .env.example)
API_KEY = os.getenv("XAI_API_KEY")
# NOTE: API_BASE_URL in .env is the FULL chat/completions URL — use it directly
API_BASE_URL = os.getenv("API_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")


def generate_response(prompt: str):
    # API_BASE_URL already contains the full endpoint URL
    url = API_BASE_URL

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
        # Increased timeout to 60s for reasoning-heavy models (Grok)
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"LLM API Error: {response.status_code} - {response.text}")
            return f"[ERROR] The AI could not generate a response (Status {response.status_code})."

    except requests.exceptions.Timeout:
        print("LLM Connection Error: Request timed out after 60s.")
        return "[ERROR] The AI service timed out. Please try again."

    except Exception as e:
        print(f"LLM Connection Error: {e}")
        import traceback
        traceback.print_exc()
        return "[ERROR] Connection to the AI service failed."
