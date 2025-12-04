import os
import json
import time
from pathlib import Path
from src.utils import group_images_by_session
from src.parsers.session_parser import parse_recipe_session

RAW_DIR = "recipe_parsing/data/test_batch"
PARSED_DIR = "recipe_parsing/data/parsed_test"

def save_recipes(recipes, output_base_dir):
    """Save parsed recipes to JSON files in language-specific folders."""
    
    for recipe in recipes:
        # Determine output folder based on language
        lang = recipe.get('language', 'en')
        if lang == 'original':
            output_dir = Path(output_base_dir) / "original_language"
        else:
            output_dir = Path(output_base_dir) / "english"
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        recipe_name = recipe.get('name', 'Untitled')
        if not recipe_name:
            recipe_name = 'Untitled'
            
        safe_name = recipe_name.lower().replace(' ', '_').replace('/', '_')
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        safe_name = safe_name[:100]
        
        output_path = output_dir / f"{safe_name}_parsed.json"
        
        # Handle filename collisions
        counter = 2
        while output_path.exists():
            output_path = output_dir / f"{safe_name}_part_{counter}_parsed.json"
            counter += 1
        
        with open(output_path, 'w') as f:
            json.dump(recipe, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved: {output_path.parent.name}/{output_path.name}")

def run_test():
    print("============================================")
    print("Starting Test Batch Ingestion")
    print("============================================")
    
    # 1. Group images
    print(f"Grouping images in {RAW_DIR}...")
    groups = group_images_by_session(RAW_DIR)
    print(f"Found {len(groups)} sessions.")
    
    # 2. Process by group
    for i, group in enumerate(groups):
        print(f"\n[Session {i+1}/{len(groups)}] Processing {len(group)} images: {group}")
        
        # Construct full paths
        image_paths = [os.path.join(RAW_DIR, f) for f in group]
        
        try:
            # Call Session Parser
            recipes = parse_recipe_session(image_paths)
            
            if recipes:
                save_recipes(recipes, PARSED_DIR)
            else:
                print("  ⊘ No recipes found in session.")
                
        except Exception as e:
            print(f"  ❌ Error processing session {i+1}: {e}")
            import traceback
            traceback.print_exc()
            
        # Rate limiting
        time.sleep(2)

if __name__ == "__main__":
    run_test()
