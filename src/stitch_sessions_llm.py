import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai
from utils_legacy import group_images_by_session

# Configuration
PARSED_DIR = "data/parsed/english"
MERGED_DIR = "data/merged_llm"
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=API_KEY)

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
        fname = r.get('source_metadata', {}).get('filename')
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
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Group by image for clearer context
    images_map = {}
    for r in session_recipes:
        img = r.get('source_metadata', {}).get('filename', 'unknown')
        if img not in images_map:
            images_map[img] = []
        images_map[img].append({
            "id": r.get('name'),
            "type": r.get('recipe_type'),
            "ingredients_preview": r.get('ingredients', [])[:5]
        })
    
    # Sort images by name/time (assuming filenames are sequential/timestamped)
    sorted_images = sorted(images_map.keys())
    
    structured_context = []
    for img in sorted_images:
        structured_context.append({
            "image_filename": img,
            "recipes_found": images_map[img]
        })
        
    prompt = f"""
    You are an expert chef organizing a digital recipe book.
    I have a group of recipe fragments from a photo session.
    They are presented in CHRONOLOGICAL ORDER (Image 1, Image 2, etc.).
    
    Your goal is to merge them into coherent Dishes.
    
    Here is the sequence:
    {json.dumps(structured_context, indent=2)}
    
    RULES:
    1. Identify the MAIN DISH(es).
    2. Group COMPONENT recipes (sauces, fillings, preps) under their Main Dish.
    3. **CRITICAL**: "Finishing", "To Serve", "Acabado y Presentación", or "Assembly" recipes OFTEN belong to a Main Dish from a PREVIOUS image. Look at the sequence.
    4. If a component is named "Sauce" or "Garnish" and follows a Main Dish, it likely belongs to it.
    5. If there are multiple Main Dishes, keep them separate.
    
    OUTPUT FORMAT (JSON ONLY):
    {{
      "dishes": [
        {{
          "main_recipe_id": "Name of Main Recipe",
          "component_ids": ["Name of Component 1", "Name of Component 2"],
          "is_new_name": boolean
        }}
      ],
      "orphans": ["Name of any recipe that doesn't fit anywhere"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Extract JSON from response
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        return json.loads(text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

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

import PIL.Image

def analyze_image_pair(image1_path: str, image1_data: Dict, image2_path: str, image2_data: Dict) -> Dict:
    model = genai.GenerativeModel('gemini-2.0-flash')
    
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
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def main():
    print("Starting LLM Session Stitcher (Multimodal Sliding Window)...")
    
    all_recipes = load_parsed_recipes(PARSED_DIR)
    sessions = group_recipes_by_session(all_recipes)
    print(f"Found {len(all_recipes)} recipes in {len(sessions)} sessions.")
    
    output_path = Path(MERGED_DIR)
    output_path.mkdir(exist_ok=True)
    
    # Map for quick access
    recipe_map = {r['name']: r for r in all_recipes}
    
    for i, session in enumerate(sessions):
        print(f"\nProcessing Session {i+1} ({len(session)} recipes)...")
        
        # 1. Group by Image within Session
        images_in_session = {}
        for r in session:
            fname = r.get('source_metadata', {}).get('filename')
            if fname not in images_in_session:
                images_in_session[fname] = []
            images_in_session[fname].append(r)
            
        sorted_images = sorted(images_in_session.keys())
        
        merges_to_apply = []
        
        for j in range(len(sorted_images) - 1):
            img1_name = sorted_images[j]
            img2_name = sorted_images[j+1]
            
            recipes1 = images_in_session[img1_name]
            recipes2 = images_in_session[img2_name]
            
            # TRIGGER CONDITION: General Multimodal Lookahead
            # We check ALL sequential pairs in a session because complex recipes often span pages.
            # The cost is higher (more LLM calls), but it guarantees we catch "Mugaritz-style" splits.
            
            print(f"  Analyzing Pair: {img1_name} -> {img2_name}")
            
            # Get absolute paths for images
            img1_path = recipes1[0].get('source_metadata', {}).get('abs_path')
            img2_path = recipes2[0].get('source_metadata', {}).get('abs_path')
            
            if not img1_path or not img2_path:
                print("    Missing image paths, skipping visual check.")
                continue
                
            data1 = {"filename": img1_name, "recipes": [{"name": r['name'], "type": r['recipe_type'], "ingredients": r['ingredients'][:5]} for r in recipes1]}
            data2 = {"filename": img2_name, "recipes": [{"name": r['name'], "type": r['recipe_type'], "ingredients": r['ingredients'][:5]} for r in recipes2]}
            
            result = analyze_image_pair(img1_path, data1, img2_path, data2)
            
            if result and result.get('merges'):
                print(f"    Found merges: {result['merges']}")
                merges_to_apply.extend(result['merges'])
                
        # 3. Apply Merges
        skipped_ids = set()
        
        def get_id(r):
            return f"{r.get('source_metadata', {}).get('filename')}_{r['name']}"
        
        for merge in merges_to_apply:
            main_name = merge['main_recipe_name']
            comp_name = merge['component_to_merge']
            
            if main_name in recipe_map and comp_name in recipe_map:
                main_r = recipe_map[main_name]
                comp_r = recipe_map[comp_name]
                
                # Prevent merging into self
                if get_id(main_r) == get_id(comp_r):
                    continue
                
                # Merge content
                main_r.setdefault('ingredients', []).extend(comp_r.get('ingredients', []))
                main_r.setdefault('steps', []).extend(comp_r.get('steps', []))
                main_r.setdefault('source_files', []).append(comp_r.get('source_metadata', {}).get('filename'))
                
                skipped_ids.add(get_id(comp_r))
                
        # 4. Save Final
        for r in session:
            # Check ID instead of name
            if get_id(r) in skipped_ids:
                continue
            
            safe_name = r['name'].replace(" ", "_").replace("/", "_").replace("\\", "_").lower()
            with open(output_path / f"{safe_name}_merged.json", 'w', encoding='utf-8') as f:
                json.dump(r, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
