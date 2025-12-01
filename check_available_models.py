import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from src.config import get_chat_client

def main():
    client = get_chat_client()
    try:
        print("Querying available models from proxy...")
        models = client.models.list()
        print(f"Found {len(models.data)} models:")
        for model in models.data:
            print(f"- {model.id}")
    except Exception as e:
        print(f"Error listing models: {e}")
        print("\nAttempting manual probe of common models...")
        # Fallback: try specific models
        test_models = ["gpt-4-turbo", "claude-3-5-sonnet", "gemini-1.5-pro", "llama-3-70b"]
        for model_id in test_models:
            try:
                client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                print(f"- {model_id}: AVAILABLE")
            except Exception as inner_e:
                print(f"- {model_id}: NOT AVAILABLE ({inner_e})")

if __name__ == "__main__":
    main()
