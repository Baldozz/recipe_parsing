import google.generativeai as genai
import os
from src.config import get_chat_client

# Check via google.generativeai
print("--- Google Generative AI Models ---")
api_key = os.environ["GEMINI_API_KEY"]
genai.configure(api_key=api_key)
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing custom models: {e}")

# Check via OpenAI client
print("\n--- OpenAI Compatible Models ---")
try:
    client = get_chat_client()
    # OpenAI client doesn't always support listing models on 3rd party endpoints the same way, but let's try
    models = client.models.list()
    for m in models:
        print(m.id)
except Exception as e:
    print(f"Error listing OpenAI models: {e}")
