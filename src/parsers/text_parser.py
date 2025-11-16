import json
from src.config import get_chat_client, CHAT_MODEL

def parse_recipe_text(text: str, model: str | None = None) -> dict:
    client = get_chat_client()
    model = model or CHAT_MODEL

    prompt = """You are a recipe extraction assistant. Analyze the following recipe text and convert it into a structured JSON format.

The JSON must have exactly these fields:
- "name": string
- "ingredients": array of strings
- "steps": array of strings
- "other_details": object

Use [] or {} when information is missing.
Output ONLY valid JSON, nothing else."""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise recipe parser that outputs only valid JSON."},
            {"role": "user", "content": prompt + "\n\nHere is the recipe text:\n\n" + text},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    return json.loads(resp.choices[0].message.content)
