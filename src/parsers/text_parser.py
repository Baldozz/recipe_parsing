import json
from src.config import get_chat_client, CHAT_MODEL

def parse_recipe_text(text: str, model: str | None = None) -> list[dict]:
    """
    Parse recipe text and extract one or more recipes.
    
    Returns:
        list[dict]: List of recipe dictionaries, each with fields:
            - name: string
            - ingredients: array of strings
            - steps: array of strings
            - other_details: object
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    prompt = """You are a recipe extraction assistant. Analyze the following text and extract ALL recipes found.

IMPORTANT: The text may contain:
- A single recipe
- Multiple recipes (extract each one separately)
- A partial recipe (part of a recipe split across documents)

For each recipe found, create a JSON object with exactly these fields:
- "name": string (the recipe name/title)
- "ingredients": array of strings (each ingredient as a separate item)
- "steps": array of strings (each step as a separate item, in order)
- "other_details": object (any additional information like cook time, servings, temperature, notes, etc.)

If a recipe appears to be incomplete or partial (e.g., has "(Part 1)", "(continued)", or is missing ingredients/steps), still extract it but preserve any part indicators in the name.

Return a JSON object with a "recipes" array containing all found recipes:
{
  "recipes": [
    {"name": "...", "ingredients": [...], "steps": [...], "other_details": {...}},
    {"name": "...", "ingredients": [...], "steps": [...], "other_details": {...}}
  ]
}

If only one recipe is found, the array will have one element.
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

    result = json.loads(resp.choices[0].message.content)
    
    # Handle both new format (with "recipes" key) and potential old format
    if "recipes" in result:
        return result["recipes"]
    else:
        # If LLM returns single recipe object, wrap it in a list
        return [result]
