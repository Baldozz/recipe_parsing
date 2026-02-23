import time


def call_model_with_retry(model, prompt, max_retries=5, initial_delay=2):
    """Call a Gemini GenerativeModel with exponential backoff on 429."""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            if "429" in str(e) or "Resource exhausted" in str(e):
                if attempt == max_retries - 1:
                    raise e
                print(f"Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
