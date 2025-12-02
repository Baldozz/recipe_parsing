from src.config import get_chat_client
import json

def main():
    client = get_chat_client()
    print("Testing gemini-1.5-pro...")
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-pro",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("Success!")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
