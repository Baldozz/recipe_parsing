from src.config import get_chat_client, CHAT_MODEL
import json

def main():
    client = get_chat_client()
    print(f"Testing {CHAT_MODEL} with Google API...")
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10
        )
        print("Success!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
