import os
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai
import PIL.Image
from datetime import datetime

from src.config import CHAT_MODEL
from src.parsers.recipe_merger import detect_recipe_part, merge_recipe_parts
from src.utils.json_utils import extract_json_from_text

# Configuration
PARSED_DIR = "data/parsed/images"
MERGED_DIR = "data/merged_llm"
RAW_IMG_DIR = Path("data/raw/jpg_recipes")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def load_parsed_recipes(parsed_dir: str) -> List[Dict]:
    recipes = []
    path = Path(parsed_dir)
    # Recursively find all json files
    for file_path in path.rglob("*_parsed.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Ensure source_metadata exists for grouping
                if 'source_metadata' not in data:
                    data['source_metadata'] = {'filename': file_path.name}
                recipes.append(data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    return recipes

def group_recipes_by_session(recipes: List[Dict]) -> List[List[Dict]]:
    # Extract filenames to use existing grouping logic
    filename_to_recipes = {}
    for r in recipes:
        meta = r.get('source_metadata', {})
        fname = meta.get('filename')
        
        # Fallback for image groups which use 'source_files' list
        if not fname and 'source_files' in meta and meta['source_files']:
             # Use the first image in the group as the representative filename
             fname = meta['source_files'][0]
             # Store it back so later logic finds it consistently
             meta['filename'] = fname
             
        if fname:
            if fname not in filename_to_recipes:
                filename_to_recipes[fname] = []
            filename_to_recipes[fname].append(r)
            
    # Use the REAL utility from utils.py
    # We need to pass a dummy folder path because utils scans the folder, 
    # but here we want to group *our* list of files.
    # So we'll just use the logic from utils but adapted here, OR better:
    # Let's trust the utils logic I just updated which handles IMG_XXXX.
    
    all_filenames = list(filename_to_recipes.keys())
    all_filenames.sort()
    
    # Re-implementing the updated logic from utils.py here to avoid import complexity
    # (Since utils.py scans a folder, but we have a list of files from JSONs)
    
    sessions = []
    if not all_filenames:
        return []
        
    # Helper to get time/seq from filename
    def get_time_value(fname):
        try:
            if 'IMG_' in fname:
                # IMG_1495.JPG -> 1495
                return int(fname.split('IMG_')[1].split('.')[0])
            else:
                # 20190828_185319.jpg -> timestamp
                t_str = fname.split('.')[0]
                # Handle suffixes
                if '_' in t_str and len(t_str.split('_')) > 2:
                     parts = t_str.split('_')
                     t_str = f"{parts[0]}_{parts[1]}"
                dt = datetime.strptime(t_str, "%Y%m%d_%H%M%S")
                return dt.timestamp()
        except:
            return None

    current_session = []
    last_time = None
    
    for fname in all_filenames:
        t = get_time_value(fname)
        if t is None:
            # Unknown format, standalone
            if current_session:
                sessions.append(current_session)
            sessions.append([fname])
            current_session = []
            last_time = None
            continue
            
        if not current_session:
            current_session.append(fname)
            last_time = t
            continue
            
        # Delta check (60 seconds/units)
        if (t - last_time) <= 60:
            current_session.append(fname)
            last_time = t
        else:
            sessions.append(current_session)
            current_session = [fname]
            last_time = t
            
    if current_session:
        sessions.append(current_session)
        
    # Map back to recipes
    recipe_sessions = []
    for session_files in sessions:
        session_recipes = []
        for fname in session_files:
            session_recipes.extend(filename_to_recipes.get(fname, []))
        if session_recipes:
            recipe_sessions.append(session_recipes)
            
    return recipe_sessions

def analyze_session_with_llm(session_recipes: List[Dict]) -> Dict:
    """
    Ask the LLM to identify which recipe fragments belong together across
    the entire session, using full ingredient lists and step previews as
    context (not just the first 5 ingredients as before).

    Returns a plan dict: {"merges": [{"main_recipe_name": ...,
                                       "component_to_merge": ...}, ...]}
    This matches the format consumed by the merge-application logic in main().
    """
    model = genai.GenerativeModel(CHAT_MODEL)

    # Group by source image, sorted chronologically
    images_map: Dict[str, list] = {}
    for r in session_recipes:
        img = r.get("source_metadata", {}).get("filename", "unknown")
        if img not in images_map:
            images_map[img] = []
        images_map[img].append({
            "name": r.get("name"),
            "type": r.get("recipe_type"),
            "related_to": r.get("related_to"),
            "ingredients": r.get("ingredients", []),       # full list
            "steps_preview": r.get("steps", [])[:3],       # first 3 steps
        })

    sorted_images = sorted(images_map.keys())
    structured_context = [
        {"image_filename": img, "recipes_found": images_map[img]}
        for img in sorted_images
    ]

    prompt = f"""You are an expert chef organising a digital recipe archive.
I have parsed recipe fragments from a chronological photo session (Image 1 → Image N).
Each fragment was extracted from a single page of a cookbook or notebook.

SESSION DATA:
{json.dumps(structured_context, indent=2, ensure_ascii=False)}

TASK: Identify which fragments must be MERGED into the same final dish.

MERGE RULES:
1. "To Serve", "Finishing", "Assembly", "Acabado y Presentación" fragments
   almost always belong to the Main Dish from the PREVIOUS image(s).
2. A fragment with only steps (no title, no ingredients) continues the dish above it.
3. A named component (e.g. "Duck Sauce") belongs to the main dish it logically serves.
4. Two fragments with the same or very similar names from consecutive images are the
   same recipe split across pages — merge them.
5. If a fragment's `related_to` field already names a parent, honour it.
6. Do NOT merge unrelated dishes (e.g. "Tomato Soup" and "Chocolate Cake").

OUTPUT FORMAT — JSON only, no markdown:
{{
  "merges": [
    {{
      "main_recipe_name": "Exact name of the parent recipe (as it appears in the data)",
      "component_to_merge": "Exact name of the child/component to absorb into the parent"
    }}
  ]
}}

If nothing needs merging, return: {{"merges": []}}
"""

    try:
        response = model.generate_content(prompt)
        result = json.loads(extract_json_from_text(response.text))
        # Normalise: accept both "merges" and legacy "dishes" keys
        if "dishes" in result and "merges" not in result:
            merges = []
            for dish in result["dishes"]:
                main = dish.get("main_recipe_id", "")
                for comp in dish.get("component_ids", []):
                    merges.append({"main_recipe_name": main, "component_to_merge": comp})
            return {"merges": merges}
        return result
    except Exception as e:
        print(f"LLM Error in analyze_session_with_llm: {e}")
        return {"merges": []}

def merge_based_on_plan(session_recipes: List[Dict], plan: Dict, output_dir: Path):
    # Map name -> recipe data
    recipe_map = {r['name']: r for r in session_recipes}
    
    if not plan or 'dishes' not in plan:
        print("Invalid plan, skipping merge.")
        return

    for dish in plan['dishes']:
        main_name = dish['main_recipe_id']
        components = dish.get('component_ids', [])
        
        # Find or Create Main
        if main_name in recipe_map:
            main_recipe = recipe_map[main_name]
        else:
            # If LLM suggested a new name, pick the first component as base or create empty
            # For now, let's try to find a 'main' type in the components to promote
            main_recipe = None
            for c_name in components:
                if c_name in recipe_map and recipe_map[c_name].get('recipe_type') == 'main':
                    main_recipe = recipe_map[c_name]
                    main_name = c_name # Update name
                    components.remove(c_name) # Remove from components list
                    break
            
            if not main_recipe and components:
                 # Pick the first one as base
                 main_recipe = recipe_map[components[0]]
                 components.pop(0)
        
        if not main_recipe:
            continue

        # Merge Components
        for comp_name in components:
            if comp_name not in recipe_map:
                continue
                
            comp = recipe_map[comp_name]
            print(f"  Merging '{comp_name}' into '{main_name}'")
            
            # Merge Logic (Simplified)
            main_recipe.setdefault('ingredients', []).extend(comp.get('ingredients', []))
            main_recipe.setdefault('steps', []).extend(comp.get('steps', []))
            main_recipe.setdefault('source_files', []).append(comp.get('source_metadata', {}).get('filename'))
            
        # Save
        safe_name = main_name.replace(" ", "_").replace("/", "_").replace("\\", "_").lower()
        out_path = output_dir / f"{safe_name}_merged.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(main_recipe, f, indent=2, ensure_ascii=False)
            
    # Handle Orphans (Save as is)
    for orphan_name in plan.get('orphans', []):
        if orphan_name in recipe_map:
            r = recipe_map[orphan_name]
            safe_name = orphan_name.replace(" ", "_").replace("/", "_").replace("\\", "_").lower()
            out_path = output_dir / f"{safe_name}_merged.json"
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(r, f, indent=2, ensure_ascii=False)

def analyze_image_pair(image1_path: str, image1_data: Dict, image2_path: str, image2_data: Dict) -> Dict:
    model = genai.GenerativeModel(CHAT_MODEL)
    
    # Load Images
    try:
        img1 = PIL.Image.open(image1_path)
        img2 = PIL.Image.open(image2_path)
    except Exception as e:
        print(f"Error loading images: {e}")
        return None
    
    context_text = json.dumps([
        {"image": image1_data['filename'], "recipes": image1_data['recipes']},
        {"image": image2_data['filename'], "recipes": image2_data['recipes']}
    ], indent=2)
        
    prompt = """
    You are an expert chef and archivist digitizing a complex cookbook.
    I have extracted recipe fragments from two sequential pages (Image 1 -> Image 2).
    
    The parser often splits a single complex recipe into multiple small fragments (e.g. "Main", "Sauce", "Finishing").
    
    Your goal: Reconstruct the original recipe structure by looking at the IMAGES and JSON.
    
    TASK:
    1. Look at Image 1 and Image 2. Do they look like pages of the same recipe? (e.g. same visual style, text flowing from bottom of 1 to top of 2).
    2. Look at the JSON fragments. Do the fragments in Image 2 belong to the dish started in Image 1?
       - Example: Image 1 has "Duck Breast", Image 2 has "Duck Sauce" and "To Serve". -> MERGE ALL into "Duck Breast".
    3. If Image 1 and Image 2 contain DIFFERENT, unrelated recipes, keep them separate.
    
    OUTPUT JSON:
    {
      "merges": [
        {
          "main_recipe_name": "Name of the Parent Recipe (usually from Image 1)",
          "component_to_merge": "Name of the Child Fragment (from Image 1 or Image 2)",
          "reason": "Visual flow / Component relationship"
        }
      ]
    }
    """
    
    try:
        # Pass both images and text
        response = model.generate_content([prompt, "Context Data:", context_text, "Image 1:", img1, "Image 2:", img2])
        return json.loads(extract_json_from_text(response.text))
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def normalize_name(name: str) -> str:
    """Normalize name for fuzzy matching."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def cleanup_using_metadata(merged_dir: Path):
    """
    Perform a deterministic cleanup pass using 'related_to' metadata.
    Merges any surviving orphan files into their explicit parents.
    """
    print("\n--- Starting Automatic Metadata Cleanup ---")
    
    recipes = []
    # Reload from disk to get state after LLM stitching
    for f in merged_dir.glob("*_merged.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                data['_filepath'] = f 
                recipes.append(data)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    # Index by normalized name AND exact name
    name_map = {}
    for r in recipes:
        name_map[normalize_name(r.get('name'))] = r
        name_map[r.get('name')] = r
        
    merges_count = 0
    
    for child in recipes:
        related = child.get('related_to')
        if not related:
            continue
            
        child_name = child.get('name')
        
        # Find Parent
        parent = name_map.get(normalize_name(related)) or name_map.get(related)
        
        if parent:
            parent_name = parent.get('name')
            
            # Prevent self-merge or loop if parent refers to child (unlikely but safe)
            if child['_filepath'] == parent['_filepath']:
                continue
            
            print(f"  [Cleanup] Merging '{child_name}' -> '{parent_name}' (via metadata)")
            
            # Merge content
            parent.setdefault('ingredients', []).extend(child.get('ingredients', []))
            parent.setdefault('steps', []).extend(child.get('steps', []))
            
            if 'source_files' in child.get('source_metadata', {}):
                 parent.setdefault('source_metadata', {}).setdefault('source_files', []).extend(
                     child['source_metadata']['source_files']
                 )
            
            # Save Parent
            save_path = parent['_filepath']
            if '_filepath' in parent:
                del parent['_filepath']
            
            # Ensure image link
            if 'source_metadata' in parent:
                fname = parent['source_metadata'].get('filename')
                if fname and 'image_path' not in parent['source_metadata']:
                     parent['source_metadata']['image_path'] = f"data/raw/jpg_recipes/{fname}"

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(parent, f, indent=2, ensure_ascii=False)
            
            # Restore key
            parent['_filepath'] = save_path
                
            # DELETE Child
            try:
                os.remove(child['_filepath'])
                merges_count += 1
            except Exception as e:
                print(f"Error deleting {child['_filepath']}: {e}")
            
    print(f"Metadata Cleanup Complete. Merged {merges_count} orphans.\n")

def _find_recipe(name: str, recipe_map: Dict[str, Any]) -> Any:
    """
    Look up a recipe by name with normalised fallback.

    Exact match is tried first; if that fails, normalised (lowercase,
    alphanumeric only) comparison is used so that accent or capitalisation
    differences between the LLM's suggestion and the parsed name don't
    silently drop a merge.
    """
    if name in recipe_map:
        return recipe_map[name]
    norm = normalize_name(name)
    for k, v in recipe_map.items():
        if normalize_name(k) == norm:
            return v
    return None


def _apply_merges(merges_to_apply: list, session: List[Dict], recipe_map: Dict) -> set:
    """
    Apply a list of merge directives to a session's recipes.

    Uses transitive root-finding so that A→B→C chains all end up in A.
    Returns the set of recipe IDs that were absorbed (should not be saved).
    """
    def get_id(r):
        return f"{r.get('source_metadata', {}).get('filename')}_{r['name']}"

    id_to_recipe = {get_id(r): r for r in session}
    parent_map: Dict[str, str] = {}

    def find_root(node_id):
        current, visited = node_id, set()
        while current in parent_map:
            if current in visited:
                break
            visited.add(current)
            current = parent_map[current]
        return current

    for merge in merges_to_apply:
        main_name = merge.get("main_recipe_name", "")
        comp_name = merge.get("component_to_merge", "")

        main_r = _find_recipe(main_name, recipe_map)
        comp_r  = _find_recipe(comp_name, recipe_map)

        if not main_r or not comp_r:
            print(f"    [Skip] Could not resolve merge: '{comp_name}' → '{main_name}'")
            continue

        main_id = get_id(main_r)
        comp_id = get_id(comp_r)

        if main_id == comp_id:
            continue
        if find_root(main_id) == comp_id:
            print(f"    [Cycle] Skipping merge of '{comp_name}' into '{main_name}'")
            continue

        parent_map[comp_id] = main_id

    skipped_ids: set = set()

    for child_id in parent_map:
        root_id = find_root(child_id)
        if root_id not in id_to_recipe or child_id not in id_to_recipe:
            continue

        root  = id_to_recipe[root_id]
        child = id_to_recipe[child_id]

        root.setdefault("ingredients", []).extend(child.get("ingredients", []))
        root.setdefault("steps", []).extend(child.get("steps", []))

        root_meta  = root.setdefault("source_metadata", {"source_files": []})
        child_meta = child.get("source_metadata", {})

        if "source_files" not in root_meta:
            root_meta["source_files"] = []
            if "filename" in root_meta:
                root_meta["source_files"].append(root_meta["filename"])

        child_fname = child_meta.get("filename")
        if child_fname and child_fname not in root_meta["source_files"]:
            root_meta["source_files"].append(child_fname)

        for f in child_meta.get("source_files", []):
            if f not in root_meta["source_files"]:
                root_meta["source_files"].append(f)

        skipped_ids.add(child_id)

    return skipped_ids


def main():
    print("Starting LLM Session Stitcher...")

    all_recipes = load_parsed_recipes(PARSED_DIR)
    sessions = group_recipes_by_session(all_recipes)
    print(f"Found {len(all_recipes)} recipes in {len(sessions)} sessions.")

    output_path = Path(MERGED_DIR)
    output_path.mkdir(exist_ok=True)

    # Global name → recipe lookup (exact names from parsed JSON)
    recipe_map: Dict[str, Any] = {r["name"]: r for r in all_recipes}

    for i, session in enumerate(sessions):
        print(f"\nProcessing Session {i+1} ({len(session)} recipes)...")

        images_in_session: Dict[str, list] = {}
        for r in session:
            fname = r.get("source_metadata", {}).get("filename")
            if fname not in images_in_session:
                images_in_session[fname] = []
            images_in_session[fname].append(r)

        sorted_images = sorted(images_in_session.keys())
        merges_to_apply: list = []

        if len(sorted_images) <= 1:
            # Single-image session: nothing to stitch
            pass
        elif len(sorted_images) <= 10:
            # --- Session-level analysis (preferred) ---
            # One LLM call sees the FULL session context at once.
            print(f"  Using session-level analysis ({len(sorted_images)} images).")
            result = analyze_session_with_llm(session)
            if result and result.get("merges"):
                print(f"  Session merges proposed: {len(result['merges'])}")
                merges_to_apply.extend(result["merges"])
        else:
            # --- Pairwise visual fallback for very long sessions ---
            # Falls back to the original sliding-window visual check when the
            # session is too large for a single text-context call to be reliable.
            print(f"  Large session ({len(sorted_images)} images) — using pairwise visual analysis.")
            for j in range(len(sorted_images) - 1):
                img1_name = sorted_images[j]
                img2_name = sorted_images[j + 1]

                img1_path = RAW_IMG_DIR / img1_name
                img2_path = RAW_IMG_DIR / img2_name

                if not img1_path.exists() or not img2_path.exists():
                    print(f"    Missing raw image for pair ({img1_name}, {img2_name}), skipping.")
                    continue

                recipes1 = images_in_session[img1_name]
                recipes2 = images_in_session[img2_name]

                data1 = {
                    "filename": img1_name,
                    "recipes": [
                        {"name": r["name"], "type": r.get("recipe_type"),
                         "ingredients": r.get("ingredients", [])}
                        for r in recipes1
                    ],
                }
                data2 = {
                    "filename": img2_name,
                    "recipes": [
                        {"name": r["name"], "type": r.get("recipe_type"),
                         "ingredients": r.get("ingredients", [])}
                        for r in recipes2
                    ],
                }

                print(f"  Analyzing pair: {img1_name} → {img2_name}")
                result = analyze_image_pair(img1_path, data1, img2_path, data2)
                if result and result.get("merges"):
                    merges_to_apply.extend(result["merges"])

        # --- Apply merges with transitive root-finding ---
        skipped_ids = _apply_merges(merges_to_apply, session, recipe_map)

        # --- Save survivors ---
        def get_id(r):
            return f"{r.get('source_metadata', {}).get('filename')}_{r['name']}"

        for r in session:
            if get_id(r) in skipped_ids:
                continue

            safe_name = (
                r["name"]
                .replace(" ", "_").replace("/", "_").replace("\\", "_")
                .lower()
            )

            if "source_metadata" in r:
                fname = r["source_metadata"].get("filename")
                if fname:
                    r["source_metadata"]["image_path"] = str(RAW_IMG_DIR / fname)

            with open(output_path / f"{safe_name}_merged.json", "w", encoding="utf-8") as f:
                json.dump(r, f, indent=2, ensure_ascii=False)

    # --- Deterministic cleanup passes ---
    cleanup_using_metadata(output_path)
    _merge_name_parts_in_dir(output_path)


def _merge_name_parts_in_dir(merged_dir: Path) -> None:
    """
    Post-stitch pass: merge files whose names contain "Part 1", "Part 2",
    "continued", etc. using the recipe_merger utility.
    """
    print("\n--- Stitch post-process: merging named parts ---")
    groups: Dict[str, list] = {}

    for f in merged_dir.glob("*_merged.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            continue
        base_name, part = detect_recipe_part(data.get("name", ""))
        key = normalize_name(base_name)
        if key not in groups:
            groups[key] = []
        groups[key].append((f, data, part))

    merged_count = 0
    for key, members in groups.items():
        if len(members) < 2 or not any(p for _, _, p in members):
            continue

        members.sort(key=lambda x: (
            int(x[2].split("_")[1]) if x[2] and x[2].startswith("part_") else
            999 if x[2] == "continued" else 0
        ))

        merged = merge_recipe_parts([d for _, d, _ in members])
        first_path = members[0][0]
        with open(first_path, "w", encoding="utf-8") as fp:
            json.dump(merged, fp, indent=2, ensure_ascii=False)
        for path, _, _ in members[1:]:
            os.remove(path)

        names = [d.get("name") for _, d, _ in members]
        print(f"  Merged: {names} → '{merged.get('name')}'")
        merged_count += 1

    print(f"  Named parts merged: {merged_count} group(s).\n")


if __name__ == "__main__":
    main()
