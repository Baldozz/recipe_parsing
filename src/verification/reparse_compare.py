from pathlib import Path
import json
import difflib
from src.parsers.multimodal_parser import parse_recipe_group
from src.config import get_chat_client

def reparse_and_compare(json_path: str):
    print(f"🔄 verifying {json_path}...")
    
    # 1. Load Existing
    p = Path(json_path)
    with open(p, 'r') as f:
        existing = json.load(f)
        
    print(f"Existing Name: {existing.get('name')}")
    
    # 2. Find Sources
    source_meta = existing.get('source_metadata', {})
    files = source_meta.get('source_files', [])
    if not files:
        # Fallback to single filename
        fname = source_meta.get('filename')
        if fname:
            files = [fname]
            
    if not files:
        print("❌ No source source_files found in metadata.")
        return

    # Construct full paths
    # Assuming they are in data/raw/jpg_recipes based on common pattern
    # But verify if 'path' key exists in metadata using that base
    base_dir = Path("data/raw/jpg_recipes")
    valid_paths = []
    for f in files:
        full = base_dir / f
        if full.exists():
            valid_paths.append(str(full))
        else:
             # Try uppercase extension switch if needed or check explicit 'image_path'
             if source_meta.get('image_path') and Path(source_meta.get('image_path')).name == f:
                 valid_paths.append(source_meta.get('image_path'))
             else:
                 print(f"⚠️ Warning: Source file {f} not found at {full}")

    if not valid_paths:
        print("❌ No valid image files found.")
        return
        
    print(f"📸 Reparsing images: {valid_paths}")
    
    # 3. Reparse (Calling LLM)
    # Note: process_images_stream might be needed if parse_recipe_images doesn't handle list paths directly?
    # Checking import... multimodal_parser usually takes a list of paths.
    
    try:
        new_recipes = parse_recipe_group(valid_paths)
    except Exception as e:
        print(f"❌ Parser Error: {e}")
        return

    if not new_recipes:
        print("❌ Parser returned no recipes.")
        return
        
    # Assume the first returned recipe is the match (or try to match by name)
    new_parse = new_recipes[0]
    
    print("\n=== ⚖️ COMPARISON ===")
    
    print(f"OLD Name: {existing.get('name')}")
    print(f"NEW Name: {new_parse.get('name')}")
    print("-" * 20)
    
    old_ing = set(existing.get('ingredients', []))
    new_ing = set(new_parse.get('ingredients', []))
    
    print(f"OLD Ingredient Count: {len(old_ing)}")
    print(f"NEW Ingredient Count: {len(new_ing)}")
    
    print("\n--- Missing in New Parse (Items present in OLD but NOT NEW) ---")
    diff_old = old_ing - new_ing
    for i in list(diff_old)[:5]: print(f" - {i}")
    if len(diff_old) > 5: print(" ...")
    
    print("\n--- New Additions (Items present in NEW but NOT OLD) ---")
    diff_new = new_ing - old_ing
    for i in list(diff_new)[:5]: print(f" + {i}")
    if len(diff_new) > 5: print(" ...")

    print("\n--- Raw Content Check (First 200 chars) ---")
    print(f"OLD: {str(existing.get('ingredients', []))[:200]}")
    print(f"NEW: {str(new_parse.get('ingredients', []))[:200]}")

if __name__ == "__main__":
    # Hardcoded target for the user request
    target = "data/english_dataset/black_marrow_merged.json"
    reparse_and_compare(target)
