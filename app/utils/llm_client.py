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


import time

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

    for attempt in range(3):
        try:
            # Increased timeout to 90s for reasoning/bottlenecks
            response = requests.post(url, headers=headers, json=payload, timeout=90)

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            
            if response.status_code == 429:
                wait_time = 5 * (attempt + 1) # More aggressive backoff for tight TPM
                print(f"Rate limited (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            else:
                print(f"LLM API Error: {response.status_code} - {response.text}")
                return f"[ERROR] The AI could not generate a response (Status {response.status_code})."

        except requests.exceptions.Timeout:
            print(f"LLM Timeout (Attempt {attempt + 1}). Retrying...")
            time.sleep(2)
            continue

        except Exception as e:
            print(f"LLM Connection Error: {e}")
            return "[ERROR] Connection to the AI service failed."
            
    return "[ERROR] Rate limit or Timeout reached after 3 attempts."
