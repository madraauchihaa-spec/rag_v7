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


class LLMError(Exception):
    """Custom exception for LLM API failures."""
    pass


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
            error_msg = f"LLM API Error: {response.status_code} - {response.text}"
            print(error_msg)
            raise LLMError(error_msg)

    except requests.exceptions.Timeout:
        error_msg = "LLM Connection Error: Request timed out after 60s."
        print(error_msg)
        raise LLMError(error_msg)

    except Exception as e:
        error_msg = f"LLM Connection Error: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        raise LLMError(error_msg)
