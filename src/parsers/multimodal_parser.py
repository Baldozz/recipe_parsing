from pathlib import Path
import os
import json
from typing import List, Dict, Any

from src.config import get_chat_client, CHAT_MODEL
from src.parsers.jpeg_parser import encode_and_compress_image

def parse_recipe_group(image_paths: List[str], model: str | None = None) -> List[dict]:
    """
    Extract recipes from a GROUP of related images (e.g. pages of a document).
    
    Args:
        image_paths: List of absolute paths to images.
        model: LLM model to use.
        
    Returns:
        list[dict]: List of recipe dictionaries found across these images.
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    if not image_paths:
        return []

    print(f"Processing Group of {len(image_paths)} images:")
    for p in image_paths:
        print(f"  - {Path(p).name}")

    # Prepare message content with multiple images
    content_payload = []
    
    # 1. Add the text prompt first
    prompt = f"""You are an expert recipe parser. I am providing {len(image_paths)} images that belong to the SAME document or context (e.g. sequential pages of a menu, or an email printed on multiple pages).

**YOUR GOAL**: Extract all distinct recipes from these images.

**CRITICAL CONTEXT RULES**:
1. **MERGE SPLIT RECIPES**: If a recipe starts on Image 1 and finishes on Image 2, output it as a SINGLE combined recipe.
2. **MULTIPLE RECIPES PER PAGE**: If a single image contains MULTIPLE distinct recipes (e.g. "Recipe A" at the top and "Recipe B" at the bottom), extract them as SEPARATE items in the list.
3. **DETECT RELATIONSHIPS**: 
   - If Image 1 has "Beetroot Soup" and Image 2 has "To serve" (describing how to serve the soup), merge "To serve" into the "Beetroot Soup" recipe as a step or sub-section.
   - OR, if they are distinct components (e.g. "Duck Breast" and "Duck Sauce"), you can keep them separate but link them using the `related_to` field.
4. **HANDWRITING WINS**: Handwritten corrections override printed text.
5. **NO CHINESE**: Exclude Chinese characters.

**Extraction Rules**:
- **Name**: Use the main title.
- **Ingredients**: Combine ingredients from all pages if they belong to the same dish.
- **Steps**: Combine steps from all pages.
- **Notes**: Extract notes. If a note says "For [Dish]", put "[Dish]" in `related_to`.

**Output Format**:
Return a JSON object with a "recipes" array. Each recipe must have:
- "_parsing_analysis": {{ "crossed_out_items": [], "handwritten_replacements": [], "merges_performed": [] }}
- "name": string
- "recipe_type": "preparation" | "component" | "main" | "assembly"
- "related_to": string | null
- "ingredients": list of strings
- "steps": list of strings
- "other_details": object
- "source_metadata": {{ "files": {json.dumps([Path(p).name for p in image_paths])} }}

**IMPORTANT**: 
- If you see "To serve" or "Assembly" on a separate page, try to attach it to the MAIN DISH it belongs to if it's obvious from context. 
- If it's not obvious, output it as a separate recipe with type "assembly".
"""
    content_payload.append({"type": "text", "text": prompt})

    # 2. Add all images
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"Warning: File not found {img_path}, skipping.")
            continue
            
        try:
            base64_image, image_ext = encode_and_compress_image(img_path)
            content_payload.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_ext};base64,{base64_image}"
                },
            })
        except Exception as e:
            print(f"Error processing image {img_path}: {e}")

    # 3. Call LLM
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise recipe parser that outputs only valid JSON. You are capable of understanding multi-page documents.",
                },
                {
                    "role": "user",
                    "content": content_payload,
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        
        recipes = result.get("recipes", [])
        if not recipes and "name" in result: # Handle single object return
            recipes = [result]
            
        print(f"  Found {len(recipes)} recipe(s) in this group.\n")
        return recipes

    except Exception as e:
        print(f"Error calling LLM for group: {e}")
        return []
