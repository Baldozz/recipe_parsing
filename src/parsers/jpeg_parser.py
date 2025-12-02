from pathlib import Path
import os
import base64
from PIL import Image
import io
import json

from src.config import get_chat_client, CHAT_MODEL


def encode_and_compress_image(image_path, max_size=2560, quality=75):
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


def parse_recipe_image(image_path: str, model: str | None = None, previous_context: list[str] | None = None) -> list[dict]:
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
    
    base64_image, image_ext = encode_and_compress_image(image_path)

    print(f"Compressed image size (approx base64 length): {len(base64_image)} chars")

    context_str = ""
    if previous_context:
        context_str = "\n\nCONTEXT - RECENTLY PROCESSED RECIPES (for continuity):\n" + "\n---\n".join(previous_context)

    prompt = f"""You are a precise recipe extraction assistant. Analyze this image and extract the recipe(s).

KEY INSTRUCTION: **GROUP COMPONENTS, BUT SPLIT DISTINCT DISHES.**

1. **Single Dish with Components**:
   - If the image contains ONE main dish with multiple parts (e.g. "Duck" + "Brine" + "Sauce"), keep them as **ONE** recipe object.
   - Use headers (starting with ##) to separate the parts.

2. **Multiple Distinct Dishes**:
   - If the image contains **MULTIPLE UNRELATED DISHES** (e.g. "Bloody Wong Tong" AND "Fermented Beetroot Soup"), **SPLIT** them into separate recipe objects.
   - **HANDLE "AND" TITLES**: If a title says "Dish A and Dish B" and there are separate instructions for both (or one is clearly a standalone component like a pickle or sauce), **SPLIT** them.
   - **SUB-RECIPES**: If the image contains distinct sub-recipes (e.g. "Taro Puree", "Taro Dough", "Curry Paste") that have their own **Ingredients** AND **Steps**, **SPLIT** them into separate recipe objects. **DO NOT** group them under a main title like "Taro Pastry".
   - **EXAMPLE**: If you see "Taro Puree" and "Taro Dough", create TWO separate recipes: "Taro Puree" and "Taro Dough".
   - **PARTIAL CONTENT**: If the title says "Dish A and Dish B" but the text *only* contains ingredients/steps for **Dish B**, name the recipe **"Dish B"**. **DO NOT** use the combined title "Dish A and Dish B".
   - **CRITICAL CONDITION**: Only split if *both* dishes have their own **Ingredients** AND **Steps**.
   - **NEGATIVE EXAMPLE**: If you see "Used in Taro Dumpling" or just a title "Taro Dumpling" without its own cooking steps, **DO NOT SPLIT IT**. Keep it as a note in `other_details`.
   - **NEGATIVE EXAMPLE**: If a section is titled **"To Serve"**, **"Assembly"**, or **"Plating"**, **DO NOT SPLIT IT**. These are steps of the main recipe. Keep them in the `steps` list.
   - **SPECIFIC OVERRIDE**: If the title is "Bloody Wong Tong and Fermented Beetroot Soup", name the recipe **"Fermented Beetroot Soup"** (since the text is about the beetroot).

3. **Handwriting**: Include relevant handwritten notes in ENGLISH only. Ignore handwritten Chinese characters.

Example of Splitting:
Image contains "Chicken Soup" and "Chocolate Cake".
Output:
{{
  "recipes": [
    {{ "name": "Chicken Soup", ... }},
    {{ "name": "Chocolate Cake", ... }}
  ]
}}

Example of Grouping:
Image contains "Taro Dumpling" with "Dough" and "Filling".
Output:
{{
  "recipes": [
    {{
      "name": "Taro Dumpling",
      "ingredients": ["## Dough", "Flour...", "## Filling", "Pork..."],
      ...
    }}
  ]
}}

**Extraction Rules:**
1. **Accuracy**: Extract quantities EXACTLY as written. Do not guess.
2. **Handwriting**: Include relevant handwritten notes in ENGLISH only. Ignore handwritten Chinese characters.
3. **Tables**: Read tables row-by-row. Ensure ingredients/steps align correctly.
   - CHECK the "CONTEXT - RECENTLY PROCESSED RECIPES" below.
   - **NAMING**: Use the **General Title** of the dish (e.g., "Colombe"), NOT the specific sub-part name (e.g., "1º impasto").
   - **SUB-PARTS**: If the page describes a specific part (e.g., "1º impasto", "Filling", "Dough"), use that name as a **HEADER** (starting with `##`) in the `ingredients` and `steps` arrays.
   - **CONTINUATIONS**:
     - If previous was "[Name]", name this "[Name] (Part 2)".
     - If previous was "[Name] (Part X)", name this "[Name] (Part X+1)".
     - **Example**: Previous "Colombe (Part 2)" -> This "Colombe (Part 3)".
   - **Example**:
     - Image says: "Colombe 1º impasto"
     - Output Name: "Colombe"
     - Ingredients: ["## 1º impasto", "Flour...", "Water..."]
   - **Example**:
     - Previous was "Colombe"
     - Image says: "Colombe 2º impasto"
     - Output Name: "Colombe (Part 2)"
     - Ingredients: ["## 2º impasto", "Sugar...", "Butter..."]

{context_str}

For each recipe found, create a JSON object with exactly these fields:
- "name": string (the recipe name/title)
- "ingredients": array of strings (use ## headers for sections)
- "steps": array of strings (use ## headers for sections)
- "other_details": object (any additional info like notes, servings)

Return a JSON object with a "recipes" array:
{{
  "recipes": [ ... ]
}}
Output ONLY valid JSON.
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
    raw_recipes = []
    if "recipes" in result:
        raw_recipes = result["recipes"]
    else:
        # If LLM returns single recipe object, wrap it in a list
        raw_recipes = [result]

    # Post-processing: Merge "empty" or "component" recipes into the previous one
    final_recipes = []
    for r in raw_recipes:
        # Check if it's an "empty" recipe (no ingredients AND no steps)
        # OR if it's a "component" (has ingredients but NO steps)
        # In our context, a valid distinct dish MUST have steps.
        has_ingredients = len(r.get("ingredients", [])) > 0
        has_steps = len(r.get("steps", [])) > 0
        
        if not has_steps:
            # It's likely a note or component split off by mistake
            if final_recipes:
                # Merge into previous recipe
                prev = final_recipes[-1]
                
                # If it has ingredients, append them to the previous recipe's ingredients
                # with a header to distinguish them
                if has_ingredients:
                    header = f"## {r.get('name', 'Component')}"
                    # Check if this header or ingredients already exist to avoid double-adding
                    # (Simple check: if header is in string representation of ingredients)
                    if header not in str(prev.get("ingredients", [])):
                        prev.setdefault("ingredients", []).append(header)
                        prev["ingredients"].extend(r["ingredients"])
                        print(f"  Merged component '{r.get('name')}' ingredients into '{prev.get('name')}'.")
                
                # Also merge notes if present
                note_content = r.get('other_details', {}).get('notes', '')
                if note_content:
                    existing_notes = prev.get("other_details", {}).get("notes", "")
                    if existing_notes:
                        prev["other_details"]["notes"] = existing_notes + "\n" + f"{r.get('name')}: {note_content}"
                    else:
                        if "other_details" not in prev:
                            prev["other_details"] = {}
                        prev["other_details"]["notes"] = f"{r.get('name')}: {note_content}"
                    print(f"  Merged component '{r.get('name')}' notes into '{prev.get('name')}'.")

            else:
                # If it's the first one, we can't merge back. Keep it.
                final_recipes.append(r)
        else:
            final_recipes.append(r)

    return final_recipes
