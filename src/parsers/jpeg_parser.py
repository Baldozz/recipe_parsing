from pathlib import Path
import os
import json

from src.config import get_chat_client, CHAT_MODEL
from src.utils.image_utils import encode_and_compress_image


def parse_recipe_image(image_path: str, model: str | None = None) -> dict:
    """
    1:1 port of your notebook version, but using get_chat_client().
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    print(f"Processing: {image_path}")
    print(f"Original file size: {os.path.getsize(image_path)} bytes")

    base64_image, image_ext = encode_and_compress_image(image_path, max_size=1200, quality=75)

    print(f"Compressed image size (approx base64 length): {len(base64_image)} chars")

    prompt = """You are a recipe extraction assistant. Analyze this recipe image and convert it into a structured JSON format.

The JSON must have exactly these fields:
- "name": string (the recipe name/title)
- "ingredients": array of strings (each ingredient as a separate item)
- "steps": array of strings (each step as a separate item, in order)
- "other_details": object (any additional information like cook time, servings, temperature, notes, etc.)

Extract all information accurately from the image. If any field cannot be determined, use an empty array [] or empty object {} as appropriate.

Output ONLY valid JSON, nothing else. If you read a special character, transform it into a character of the english language. Everything you output has to be 
human readable. For example: this should not be in the output: ba\\u00f1o . Instead, write: bano.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise recipe parser that outputs only valid JSON.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_ext};base64,{base64_image}"
                        },
                    },
                ],
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    recipe_json = json.loads(response.choices[0].message.content)
    print("Recipe parsed successfully!\n")
    return recipe_json