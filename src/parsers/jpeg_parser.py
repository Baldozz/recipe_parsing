from pathlib import Path
import os
import base64
from PIL import Image
import io
import json

from src.config import get_chat_client, CHAT_MODEL


def encode_and_compress_image(image_path, max_size=1200, quality=75):
    """Resize and recompress image before base64 encoding."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # ensure JPEG-compatible

        # Resize while keeping aspect ratio, max width/height = max_size
        img.thumbnail((max_size, max_size))

        # Save to memory as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)

        # Base64 encode
        return base64.b64encode(buffer.read()).decode("utf-8"), "jpeg"


def parse_recipe_image(image_path: str, model: str | None = None) -> list[dict]:
    """
    Extract one or more recipes from an image.
    
    Returns:
        list[dict]: List of recipe dictionaries found in the image.
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    print(f"Processing: {image_path}")
    print(f"Original file size: {os.path.getsize(image_path)} bytes")

    base64_image, image_ext = encode_and_compress_image(image_path)

    print(f"Compressed image size (approx base64 length): {len(base64_image)} chars")

    prompt = """You are a recipe extraction assistant. Analyze this image and extract ALL recipes found.

IMPORTANT: The image may contain:
- A single recipe
- Multiple recipes (extract each one separately)
- A partial recipe (part of a recipe split across images)

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
Extract all information accurately from the image. If any field cannot be determined, use an empty array [] or empty object {} as appropriate.

Output ONLY valid JSON, nothing else. If you read a special character, transform it into a character of the english language. Everything you output has to be 
human readable. For example: this should not be in the output: ba\\u00f6o . Instead, write: bano.
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

    result = json.loads(response.choices[0].message.content)
    print("Recipe(s) parsed successfully!\n")
    
    # Handle both new format (with "recipes" key) and potential old format
    if "recipes" in result:
        return result["recipes"]
    else:
        # If LLM returns single recipe object, wrap it in a list
        return [result]
