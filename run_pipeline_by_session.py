"""
Pipeline runner that processes images sequentially by session.
Passes 'previous_recipe_name' to the parser for better continuation detection.
"""
import os
import json
import time
from pathlib import Path
from src.utils import group_images_by_session
from src.parsers.jpeg_parser import parse_recipe_image # Keeping for reference if needed
from src.parsers.session_parser import parse_recipe_session

RAW_DIR = "recipe_parsing/data/raw/jpg_recipes"
PARSED_DIR = "recipe_parsing/data/parsed"

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
        
        # Add language suffix if present (legacy check, can probably remove but keeping for safety)
        # lang = recipe.get('other_details', {}).get('language', 'en')
        # if lang != 'en':
        #     safe_name += f"_{lang}"
            
        output_path = output_dir / f"{safe_name}_parsed.json"
        
        # Handle filename collisions (e.g. for continuations)
        counter = 2
        while output_path.exists():
            output_path = output_dir / f"{safe_name}_part_{counter}_parsed.json"
            counter += 1
        
        with open(output_path, 'w') as f:
            json.dump(recipe, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved: {output_path.parent.name}/{output_path.name}")

def run_pipeline():
    print("============================================")
    print("Starting Session-Aware Recipe Pipeline")
    print("============================================")
    
    # 1. Group images
    print(f"Grouping images in {RAW_DIR}...")
    groups = group_images_by_session(RAW_DIR)
    print(f"Found {len(groups)} sessions.")
    
    total_images = sum(len(g) for g in groups)
    processed_count = 0
    
    # Build map of processed images to their parsed files (for resuming)
    print("Scanning for existing parsed recipes...")
    processed_images = {} # filename -> list of parsed json paths
    if os.path.exists(PARSED_DIR):
        parsed_path = Path(PARSED_DIR)
        for json_file in parsed_path.rglob("*_parsed.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    src_file = data.get('source_metadata', {}).get('filename')
                    if src_file:
                        if src_file not in processed_images:
                            processed_images[src_file] = []
                        processed_images[src_file].append(str(json_file))
            except Exception:
                pass
    print(f"Found {len(processed_images)} already processed images.")

    # 2. Process by group
    for i, group in enumerate(groups):
        print(f"\n[Session {i+1}/{len(groups)}] Processing {len(group)} images: {group}")
        
        # Construct full paths
        image_paths = [os.path.join(RAW_DIR, f) for f in group]
        
        try:
            # Call Session Parser (One call for the whole group)
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
    run_pipeline()
