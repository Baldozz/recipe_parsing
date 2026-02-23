import time
from pathlib import Path
import os
import json
from typing import List, Optional

from src.config import get_chat_client, CHAT_MODEL
from src.utils.image_utils import encode_and_compress_image
from src.utils.json_utils import extract_json_from_text

# Maximum images sent in a single LLM call.
# Kept conservative to stay within Gemini Flash's effective context window
# for high-resolution cookbook images.
MAX_IMAGES_PER_CALL = 4


def parse_session(image_paths: List[str], model: Optional[str] = None) -> List[dict]:
    """
    Entry point: parse all images belonging to one photographic session.

    A session is a set of consecutive photos taken within the grouping
    threshold (e.g. 60 s apart).  The session is the natural unit of a
    recipe: all pages of a multi-page dish are inside it.

    - Sessions with ≤ MAX_IMAGES_PER_CALL images → one LLM call (full context).
    - Larger sessions → sliding window with 1-image overlap so the boundary
      between windows always appears in two calls, preventing lost context.
    """
    if not image_paths:
        return []

    print(f"Processing Session of {len(image_paths)} image(s):")
    for p in image_paths:
        print(f"  - {Path(p).name}")

    if len(image_paths) <= MAX_IMAGES_PER_CALL:
        return _parse_window(image_paths, model, prior_recipe_names=[])
    return _parse_session_windowed(image_paths, model)


def _parse_session_windowed(image_paths: List[str], model: Optional[str]) -> List[dict]:
    """
    Sliding window over a long session.

    Window size = MAX_IMAGES_PER_CALL.
    Stride     = MAX_IMAGES_PER_CALL - 1   (1-image overlap).

    The last image of window N is the first image of window N+1.
    This ensures a page that sits exactly on a boundary is parsed with
    context from both its predecessor and successor pages.

    Recipes already seen in a prior window (by normalised name) are
    skipped when they reappear in the overlap, preventing duplicates.
    """
    stride = MAX_IMAGES_PER_CALL - 1
    all_recipes: List[dict] = []
    seen_names: set = set()

    start = 0
    while start < len(image_paths):
        window = image_paths[start:start + MAX_IMAGES_PER_CALL]

        # Pass the names of the last few already-extracted recipes so the LLM
        # can recognise continuations rather than inventing new recipe names.
        prior_names = [r.get("name", "") for r in all_recipes[-3:] if r.get("name")]

        window_recipes = _parse_window(window, model, prior_recipe_names=prior_names)

        for r in window_recipes:
            norm = r.get("name", "").lower().strip()
            if norm and norm not in seen_names:
                seen_names.add(norm)
                all_recipes.append(r)
            # else: duplicate from the overlap region — skip

        start += stride

    return all_recipes


def _parse_window(
    image_paths: List[str],
    model: Optional[str],
    prior_recipe_names: List[str],
) -> List[dict]:
    """
    Parse one window of up to MAX_IMAGES_PER_CALL images.

    Each image is labelled PAGE N so the LLM can reason about page order.
    When prior_recipe_names is non-empty (sliding window overlap), a
    continuity note is prepended so the LLM knows what came before.
    """
    client = get_chat_client()
    model_id = (
        model.model_name if hasattr(model, "model_name") else str(model)
    ) if model else CHAT_MODEL

    # --- Build content payload: labelled pages then the instruction prompt ---
    content_payload: list = []

    valid_paths = []
    for i, img_path in enumerate(image_paths):
        if not os.path.exists(img_path):
            print(f"  Warning: file not found {img_path}, skipping.")
            continue

        content_payload.append({
            "type": "text",
            "text": f"--- PAGE {i + 1} (file: {Path(img_path).name}) ---",
        })
        try:
            # Use smaller resolution for multi-image calls to stay within
            # context window limits; single-image calls keep higher fidelity.
            max_size = 4096 if len(image_paths) == 1 else 1600
            quality  = 95   if len(image_paths) == 1 else 85
            b64, ext = encode_and_compress_image(img_path, max_size=max_size, quality=quality)
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{ext};base64,{b64}"},
            })
            valid_paths.append(img_path)
        except Exception as e:
            print(f"  Error compressing {img_path}: {e}")

    if not content_payload:
        return []

    # --- Continuity hint for sliding-window overlap ---
    continuity_note = ""
    if prior_recipe_names:
        continuity_note = (
            f"\n**CONTINUITY**: The pages immediately before this window contained "
            f"these recipes: {prior_recipe_names}. "
            f"If a page here is a continuation of one of them (e.g. 'To Serve', "
            f"steps only, no title), merge it into that recipe and set "
            f"`related_to` to the parent recipe name."
        )

    prompt = f"""You are an expert digital archivist digitizing a chef's cookbook.
I am providing {len(valid_paths)} consecutive page image(s).{continuity_note}

**YOUR GOAL**: Extract every distinct recipe with 100% DATA FIDELITY.

**CRITICAL RULES**:

1. **EXACT TRANSCRIPTION**
   - Copy quantities and ingredient names exactly as written.
   - DO NOT skip any line. Read tables row-by-row.
   - Handwritten text ALWAYS overrides printed text (e.g. "100g" crossed out, "150g" written → use "150g").
   - Crossed-out text: IGNORE unless replaced by handwriting.

2. **PAGE STRUCTURE — identify which case applies**
   - **Case A — One recipe per page**: one output object per page.
   - **Case B — Multiple recipes on one page**: one output object per recipe found.
   - **Case C — Recipe split across pages**: merge ALL fragments into ONE object;
     list all contributing page filenames in `source_files`.

3. **COMPONENTS vs CONTINUATIONS**
   - "To Serve", "Finishing", "Assembly", "Acabado y Presentación" → merge into
     the main dish they belong to (add as extra steps, not a separate recipe).
   - Distinct named sub-recipes (e.g. "Duck Sauce", "Puff Pastry Base") → keep
     separate, set `related_to` = exact name of the parent dish.

4. **ORDER INDEPENDENCE**
   - Pages may be photographed out of order (steps on page 1, ingredients on page 2).
   - Read the ENTIRE sequence before splitting into recipe objects, then reassemble.

5. **MULTILINGUAL**
   - Keep the original language text exactly as written.
   - Set `language` to the ISO-639-1 code ("it", "fr", "es", "en", etc.).
   - Do NOT translate — translation is handled downstream.

6. **CLEAN TEXT** — remove Chinese characters and Unicode garbage; keep accents (é, â, ñ).

**OUTPUT** — a JSON object with a "recipes" array. Each recipe object:
{{
  "_parsing_analysis": {{
    "crossed_out": [],
    "handwritten_overrides": [],
    "merged_pages": []
  }},
  "name": "string",
  "language": "string (ISO code)",
  "recipe_type": "main | component | preparation | assembly",
  "related_to": "string | null",
  "ingredients": ["string"],
  "steps": ["string"],
  "other_details": {{}},
  "source_files": ["page filenames that contributed to this recipe"]
}}

Output ONLY valid JSON, no markdown fences.
"""

    content_payload.append({"type": "text", "text": prompt})

    # --- Call LLM with exponential backoff on rate limits ---
    max_retries = 5
    base_delay = 5

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise recipe parser that outputs only valid JSON. "
                            "You understand multi-page documents and can reason about page order."
                        ),
                    },
                    {"role": "user", "content": content_payload},
                ],
                temperature=0,
            )

            raw = extract_json_from_text(response.choices[0].message.content)
            result = json.loads(raw)

            if isinstance(result, list):
                recipes = result
            elif isinstance(result, dict):
                recipes = result.get("recipes", [])
                if not recipes and "name" in result:
                    recipes = [result]
            else:
                print(f"  Unexpected JSON structure: {type(result)}")
                recipes = []

            print(f"  Found {len(recipes)} recipe(s) in {len(valid_paths)}-image window.\n")
            return recipes

        except Exception as e:
            err = str(e)
            if "429" in err or "Resource exhausted" in err:
                delay = base_delay * (2 ** attempt)
                print(f"  Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
            elif isinstance(e, (ValueError, KeyError)) or "delimiter" in err or "Expecting" in err:
                # Transient malformed JSON from LLM — retry
                delay = base_delay * (2 ** attempt)
                print(f"  Malformed JSON response. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  LLM error: {e}")
                return []

    print("  Max retries exceeded.")
    return []


# ---------------------------------------------------------------------------
# Backward-compatibility alias — existing call sites keep working unchanged.
# ---------------------------------------------------------------------------
def parse_recipe_group(image_paths: List[str], model=None) -> List[dict]:
    return parse_session(image_paths, model)
