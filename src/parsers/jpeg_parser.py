from pathlib import Path
import os
import base64
from PIL import Image
import io
import json

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


def parse_recipe_image(image_path: str, model: str | None = None, previous_recipe_name: str | None = None) -> list[dict]:
    """
    Extract one or more recipes from an image.
    
    Args:
        image_path: Path to image
        model: LLM model to use
        previous_recipe_name: Name of the last recipe found in this session (for linking)
    """
    client = get_chat_client()
    model = model or CHAT_MODEL

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    print(f"Processing: {image_path}")
    
    base64_image, image_ext = encode_and_compress_image(image_path)

    print(f"Compressed image size (approx base64 length): {len(base64_image)} chars")

    context_str = ""
    if previous_recipe_name:
        context_str = f"\n\n**CONTEXT - PREVIOUS RECIPE IN THIS SESSION:**\nName: \"{previous_recipe_name}\"\n"

    prompt = f"""Extract recipes from this image.

**🚨 CRITICAL RULES - READ FIRST:**

1. **HANDWRITTEN WINS**: Handwritten text overrides printed text.
   Example: Printed "100g", handwritten "200" → Extract "200g"

2. **CROSSED OUT = DELETE**: Ignore ANY text with strikethrough.
   Example: "~~lemon oil~~" → DELETE (do not extract)

3. **ACTION NOTES = STEPS**: If a note describes an ACTION (verb), put it in `steps`.
   Example: "Pour out & rest" → `steps` (NOT notes)

4. **"FOR [RECIPE]" → related_to**: Extract "For Taro Dumpling" → `"related_to": "Taro Dumpling"`

5. **NO CHINESE**: Remove all Chinese characters.

**EXTRACTION RULE: Title + Content = Recipe.**
Extract each titled section as a separate recipe.

**Recipe Types:**
- "preparation": Starts with "To [verb]"
- "component": Ingredient list used in other dishes
- "main": Complete dish
- "assembly": "To serve" / "Assembly"

Examples:
- "To ferment the beetroot" → type: "preparation"
- "Fermented Beetroot" → type: "component"  
- "Bloody Wong Tong" → type: "main"
- "To serve" → type: "assembly"

**CRITICAL: Continuation Detection**

Check the **CONTEXT - PREVIOUS RECIPE** section below.
If `previous_recipe_name` is provided, you MUST check if this page is a continuation of it.

**Mark as continuation if:**
1. **Same recipe name** as previous (even if slightly different wording)
2. **Text continues mid-sentence** from previous
3. **Enumeration continues** (e.g. previous ended at step 5, this starts at 6)
4. **Generic title** like "Seasoning", "Filling", "Dough" (implies it belongs to previous dish)
5. **No clear title** but content clearly follows previous recipe
6. **Component/Preparation following Main**: If previous was a "Main" dish (e.g. "Bloody Wong Tong...") and this is a "Preparation" (e.g. "To ferment..."), it IS a continuation.
7. **"Finish" / "To Serve"**: If the title starts with "To Finish" or "To Serve", it IS a continuation of the previous recipe.

**How to mark:**
- If continuation: Set `"is_continuation_of": "{previous_recipe_name if previous_recipe_name else 'PREVIOUS_RECIPE_NAME'}"`
- If standalone: Set `"is_continuation_of": null`

**Examples:**
- Previous: "Rabbit Stew"
- Current: "Seasoning"
- Result: `"is_continuation_of": "Rabbit Stew"`

- Previous: "Chocolate Cake"
- Current: "Apple Pie"
- Result: `"is_continuation_of": null`

**Important:** 
- Keep the original name from THIS page (e.g. "Seasoning"). Do NOT rename it to "Rabbit Stew (Part 2)".
- The post-processing script will handle the merging.

**Extraction Rules:**
1. **Accuracy**: Extract quantities EXACTLY as written. Do not guess.
2. **Handwriting**: Include relevant handwritten notes in Latin languages (English, Italian, Spanish, French, Portuguese, etc). EXCLUDE Chinese characters.
3. **Tables**: Read tables row-by-row. Ensure ingredients/steps align correctly.
   - CHECK the "CONTEXT - RECENTLY PROCESSED RECIPES" below.
   - **NAMING**:
     - **PRIORITY**: Use the **General Title** found in the **HEADER** or **COLORED BAR** at the top (e.g., "Sweet Milk" in a green bar).
     - **NOTES vs TITLE**: Any text inside a box labeled "Notes", "Note", or text that looks like a side note (e.g., "for Ma Lai Cake", "Total Batch Weight") MUST be treated as a **NOTE** in `other_details`, NEVER as the title.
     - **Example**: Top says "Sweet Milk" (Green Bar). Side box says "for Ma Lai Cake". -> Name="Sweet Milk", Notes="for Ma Lai Cake".
   - **SUB-PARTS**: If the page describes a specific part (e.g., "1º impasto", "Filling", "Dough"), use that name as a **HEADER** (starting with `##`) in the `ingredients` and `steps` arrays.
   - **TITLE INGREDIENTS**: If the title line contains an ingredient quantity (e.g., "Beef Brine - 20kg Beef Cheek"), extract that as an **INGREDIENT**, not a note.
   - **CORRECTIONS** (ABSOLUTE PRIORITY - FOLLOW THESE FIRST):
      
      - **RULE #1: HANDWRITTEN MODIFICATIONS**: 
        If you see handwritten text next to, over, or replacing printed text, **KEEP BOTH**.
        Format: `Printed Value [Handwritten Value]`
        **Example**: Printed "100g Olive Oil", handwritten "200" next to it → Extract "100g Olive Oil [200g]"
        **Example**: Printed "500ml Water", crossed out, handwritten "750ml" → Extract "500ml Water [750ml]"
        **Example**: Purely handwritten note (no printed text) → Extract as is.
      
      - **RULE #2: CROSSED OUT = DELETED (UNLESS HANDWRITTEN REPLACEMENT)**: 
        If text is crossed out AND has a handwritten replacement, use Rule #1.
        If text is crossed out with NO replacement, ignore it.
        **Example**: "lemon oil" with line through it → Do NOT include in ingredients
        **Example**: "~~200ml~~ 100g Olive Oil" → Extract ONLY "100g Olive Oil", NOT "200100g Olive Oil"
      
      - **RULE #3: NUMBER CORRECTIONS**: 
        If a number is crossed out and followed by another → use the final value only
        **Example**: "~~1000g~~ 1400g" → Extract "1400g"
   - **GROUPED QUANTITIES**: If a quantity applies to multiple items (e.g., a brace connecting Yellow and Red Peppers to "2.4kg Mixed Peppers"), extract the specific count for each (e.g. "12x Yellow Pepper") and put the shared weight in `other_details` or as a note, OR append it clearly (e.g. "12x Yellow Pepper (Total 2.4kg Mixed)").
   - **HANDWRITING CORRECTIONS**:
     - "beer check" -> "Beef Cheek"
     - "waw" -> "water"
     - "led Peppeppe" -> "Red Pepper"
     - "Miked Peppes" -> "Mixed Peppers"
     - "cougene" -> "Courgette"
     - "snery vinegar" -> "Sherry Vinegar"
     - "Graulic" -> "Garlic"
     - "1000g 1400g" -> "1400g" (Use the corrected value)
     - **UNIT CORRECTION**: If a quantity ends in "9" but looks like a weight (e.g. "1009", "509"), assume it is a handwriting error for "g" (e.g. "100g", "50g").
   - **NOTES vs STEPS** (CRITICAL):
      - **ACTION = STEP**: If a handwritten note describes an ACTION (e.g., "Pour out", "Rest overnight", "Cover", "Chill"), it MUST go into the `steps` array.
      - **NEVER** put instructions in `other_details.notes`.
      - **Example**: Note says "Pour out & rest overnight". -> Add "Pour out & rest overnight" to `steps`. Do NOT put it in `notes`.
      - **PURE NOTES ONLY**: Use `notes` field ONLY for non-action info (e.g., "Flavor is better next day").
      
      - **RULE #4: CONNECTION NOTES EXTRACTION** (MANDATORY):
        If you see phrases like "for [Recipe Name]", "used in [Recipe Name]", or "[Recipe Name]:" in the notes:
        **YOU MUST** extract the recipe name into the `related_to` field.
        **Example**: Note says "For Taro Dumpling" → Set `"related_to": "Taro Dumpling"` (NOT null!)
        **Example**: Note says "used in Ma Lai Cake" → Set `"related_to": "Ma Lai Cake"`
        **Example**: No connection mentioned → Set `"related_to": null`
      
      - **INCLUDE** other cooking tips in regular notes field.
   - **FRACTIONS**: Extract fractions like "1/2" correctly (e.g., "1/2 the water").
   - **CONTINUATIONS**:
     - If previous was "[Name]", name this "[Name] (Part 2)".
     - If previous was "[Name] (Part X)", name this "[Name] (Part X+1)".
     - **Example**: Previous "Colombe (Part 2)" -> This "Colombe (Part 3)".
     - **INFERRING NAME**: If the page has NO clear title but contains numbered steps (e.g. "10) When the dumplings...") that follow the previous recipe, **YOU MUST USE THE PREVIOUS RECIPE NAME**. Do not invent a name like "Stina nia recipe" or "Step 10".
   - **Example**:
     - Image says: "Colombe 1º impasto"
     - Output Name: "Colombe"
     - Ingredients: ["## 1º impasto", "Flour...", "Water..."]
   - **Example**:
     - Previous was "Colombe"
     - Image says: "Colombe 2º impasto"
     - Ingredients: ["## 2º impasto", "Sugar...", "Butter..."]

**MULTILINGUAL HANDLING (CRITICAL):**
1. **If the text is in English**:
   - Generate ONE recipe object.
   - Set `"language": "en"`.

2. **If the text is NOT in English** (e.g. Italian, French, Spanish, Chinese):
   - You MUST generate **TWO** recipe objects in the `recipes` list:
     a) **Original Version**: Text EXACTLY as written in the image. Set `"language": "original"`. Set `"original_language": "Italian"` (or detected language).
     b) **English Version**: Fully translated to English. Set `"language": "en"`. Set `"original_language": "Italian"` (or detected language).
   - Ensure `is_continuation_of` and `related_to` are also translated in the English version if applicable.

{context_str}

For each recipe found, create a JSON object with exactly these fields:
- "_parsing_analysis": object (CRITICAL: Fill this FIRST)
  - "crossed_out_items": list of strings (text found with strikethrough)
  - "handwritten_replacements": list of strings (e.g. "100g -> 200g")
  - "connection_notes_found": list of strings (e.g. "For Taro Dumpling")
  - "text_to_remove": list of strings (Chinese characters or non-Latin text to exclude)
- "language": string ("en" or "original")
- "original_language": string (e.g. "Italian", "French", "English")
- "has_handwriting": boolean (true if ANY handwritten text/notes/corrections were found)
- "name": string (the recipe name/title from THIS page)
- "recipe_type": string (one of: "preparation", "component", "main", "assembly")
- "is_continuation_of": string or null (name of previous recipe if this is a continuation, otherwise null)
- "related_to": string or null (if notes mention "for [Recipe Name]", extract that recipe name here)
- "ingredients": array of strings (use ## headers for sections)
- "steps": array of strings (use ## headers for sections)
- "other_details": object (any additional info like notes, servings)

**IMPORTANT**: You MUST fill `_parsing_analysis` first. 
- **FILTER STEP**: Before writing `ingredients` or `steps`, look at your `crossed_out_items` list.
- If "lemon oil" is in `crossed_out_items`, you MUST REMOVE it from the step "Put in thermomix with olive oil and lemon oil" -> "Put in thermomix with olive oil".
- If you list "100g -> 200g" in `handwritten_replacements`, you MUST use "200g" in `ingredients`.
- **FILTER NOTES**: List any Chinese text in `text_to_remove`. Then, when writing `other_details.notes`, DO NOT include that text. Keep ONLY English/Latin text.
- **DOUBLE CHECK**: Did you include any crossed-out text in the steps? If yes, DELETE IT NOW.

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
    if isinstance(result, dict) and "recipes" in result:
        raw_recipes = result["recipes"]
    elif isinstance(result, list):
        raw_recipes = result
    else:
        # If LLM returns single recipe object, wrap it in a list
        raw_recipes = [result]

    # Post-processing: Merge "empty" or "component" recipes into the previous one
    final_recipes = []
    for r in raw_recipes:
        if not isinstance(r, dict):
            print(f"  ⚠️  Skipping invalid recipe object (not a dict): {type(r)}")
            continue

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
                        new_note = f"{r.get('name')}: {note_content}"
                        if isinstance(existing_notes, list):
                            prev["other_details"]["notes"].append(new_note)
                        else:
                            # Convert to list if it was a string
                            prev["other_details"]["notes"] = [existing_notes, new_note]
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

    # Inject Source Metadata
    abs_path = os.path.abspath(image_path)
    for r in final_recipes:
        r["source_metadata"] = {
            "filename": os.path.basename(image_path),
            "path": image_path,
            "abs_path": abs_path,
            "link": f"file://{abs_path}",
            "type": "image"
        }

    return final_recipes
