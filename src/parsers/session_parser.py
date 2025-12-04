from pathlib import Path
import os
import base64
from PIL import Image
import io
import json
from typing import List, Dict, Any

from src.config import get_chat_client, CHAT_MODEL

def encode_and_compress_image(image_path, max_size=4096, quality=95):
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

def parse_recipe_session(image_paths: List[str], model: str | None = None) -> List[Dict[str, Any]]:
    """
    Extract recipes from a SEQUENCE of images (a session).
    
    Args:
        image_paths: List of paths to images in the session (ordered).
        model: LLM model to use.
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    # Validate images
    valid_paths = []
    for p in image_paths:
        if os.path.exists(p):
            valid_paths.append(p)
        else:
            print(f"⚠️ Warning: Image not found: {p}")
            
    if not valid_paths:
        return []

    print(f"Processing Session with {len(valid_paths)} images: {[os.path.basename(p) for p in valid_paths]}")
    
    # Prepare User Content (Text + Multiple Images)
    user_content = [
        {"type": "text", "text": "Extract recipes from this **SEQUENCE** of images (pages from a cookbook)."}
    ]
    
    for i, img_path in enumerate(valid_paths):
        base64_img, ext = encode_and_compress_image(img_path)
        user_content.append({
            "type": "text", 
            "text": f"--- PAGE {i+1} (Filename: {os.path.basename(img_path)}) ---"
        })
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/{ext};base64,{base64_img}"}
        })

    prompt = """
**ROLE**: You are an expert digital archivist digitizing a chef's handwritten cookbook.
**INPUT**: A sequence of images representing consecutive pages.

**OBJECTIVE**: Extract the recipes into a structured JSON format.

**🚨 CRITICAL "BOOK LOGIC" (MERGING ACROSS PAGES)**:
1. **GLOBAL CONTEXT CHECK**: Read the **ENTIRE SEQUENCE** of pages as a coherent set.
   - **ORDER INDEPENDENCE**: Sometimes pages are photographed out of order (e.g. Steps on Page 1, Ingredients on Page 2). **YOU MUST REASSEMBLE THEM**.
   - **LOOK AHEAD & BEHIND**: Check all pages in the session for connections.
   - **USE ORIGINAL TEXT FOR LINKING**: Check continuity based on the **visible text in the image** (e.g. Italian/French titles).
     - Example: If Page 1 says "Baci di Dama" and Page 2 says "Baci di Dama (Part 2)", **MERGE THEM**. Do not let translation (e.g. "Lady's Kisses") break the link.
   - If Page 1 has "Finishing" and Page 2 has "Main Dish" -> **MERGE THEM**.
   - If Page 1 has Title + Ingredients, and Page 3 has Steps -> **MERGE THEM**.
   - **DO NOT** create separate recipes like "Recipe Part 1" and "Recipe Part 2". Create **ONE** complete recipe.

2. **MULTIPLE RECIPES**:
   - If the pages contain *distinct, unrelated* recipes (e.g. Page 1 is "Soup", Page 2 is "Cake"), extract them as SEPARATE objects.

3. **HANDWRITING & CORRECTIONS**:
   - **Handwritten > Printed**: Handwritten numbers override printed ones (e.g. "100g" -> "200g").
   - **Crossed Out**: Ignore crossed-out text unless replaced.
   - **Notes**: If a note describes an ACTION ("Pour out"), put it in `steps`.

4. **MULTILINGUAL**:
   - If text is NOT English: Output TWO versions for that recipe:
     1. `language="original"` (Exact text from image)
     2. `language="en"` (Full English translation)

**OUTPUT FORMAT**:
Return a JSON object with a "recipes" array.
Each recipe object must have:
- `_parsing_analysis`: { ... } (Analysis of corrections/notes)
- `name`: string (Title)
- `ingredients`: list of strings (Combine from all pages if merged)
- `steps`: list of strings (Combine from all pages if merged)
- `source_files`: list of strings (Filenames of ALL images used for this recipe)
- `recipe_type`: string (one of: "main", "component", "preparation")
   - "main": A complete, standalone dish (e.g. "Roast Duck", "Chocolate Cake").
   - "component": A sub-recipe used as an ingredient in other dishes (e.g. "Duck Sauce", "Puff Pastry", "Almond Cream").
   - "preparation": A technique or pre-processing step (e.g. "Cleaning Artichokes", "Tempering Chocolate").
- `other_details`: { "notes": ... }

**EXAMPLE (MERGE)**:
- Page 1: "Apple Pie" (Ingredients + Steps 1-3)
- Page 2: (Steps 4-6 + "To Serve")
-> **OUTPUT**: ONE recipe "Apple Pie" containing ALL ingredients and ALL steps (1-6 + Serve). `source_files` = ["page1.jpg", "page2.jpg"].

**EXAMPLE (SEPARATE)**:
- Page 1: "Tomato Soup"
- Page 2: "Grilled Cheese"
-> **OUTPUT**: TWO recipes.

Output ONLY valid JSON.
"""

    user_content.append({"type": "text", "text": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise recipe parser. Output only valid JSON.",
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    print(f"DEBUG: Raw LLM Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    raw_recipes = []
    if isinstance(result, dict) and "recipes" in result:
        raw_recipes = result["recipes"]
    elif isinstance(result, list):
        raw_recipes = result
    else:
        raw_recipes = [result]

    # Post-processing: Check for double-wrapping (LLM hallucination)
    # Sometimes LLM returns { "recipes": [ { "recipes": [...] } ] }
    if len(raw_recipes) == 1 and isinstance(raw_recipes[0], dict) and "recipes" in raw_recipes[0]:
        print("  ⚠️  Detected double-wrapped recipes, unwrapping...")
        raw_recipes = raw_recipes[0]["recipes"]

    # Post-processing to inject source metadata
    final_recipes = []
    for r in raw_recipes:
        # If the LLM didn't populate source_files (it might forget), infer from all images
        # But ideally it should specify which pages contributed.
        # For safety, if merged, we assume it used the whole session or we trust the LLM.
        # Let's trust the LLM but fallback to all images if empty.
        if "source_files" not in r or not r["source_files"]:
             r["source_files"] = [os.path.basename(p) for p in valid_paths]
        
        # Add full metadata for the FIRST image as the primary source (for file naming)
        # But list all sources in the field.
        primary_filename = r["source_files"][0] if r["source_files"] else os.path.basename(valid_paths[0])
        
        # Find the path for the primary filename
        primary_path = next((p for p in valid_paths if os.path.basename(p) == primary_filename), valid_paths[0])
        abs_path = os.path.abspath(primary_path)
        
        r["source_metadata"] = {
            "filename": primary_filename,
            "path": primary_path,
            "abs_path": abs_path,
            "link": f"file://{abs_path}",
            "type": "image",
            "all_source_files": r["source_files"] # Keep track of all
        }
        final_recipes.append(r)

    return final_recipes
