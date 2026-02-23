import json
import shutil
import os
from pathlib import Path

def extract_english_recipes(data_dir: str = "recipe_parsing/data/linked", output_dir: str = "recipe_parsing/data/english_recipes"):
    print(f"Extracting English recipes from {data_dir} to {output_dir}...")
    
    linked_dir = Path(data_dir)
    dest_dir = Path(output_dir)
    
    # Create output directory
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True)
    
    count = 0
    
    for file_path in linked_dir.rglob("*.json"):
        try:
            with open(file_path, 'r') as f:
                recipe = json.load(f)
                
            # Check language field
            lang = recipe.get('language', 'en') # Default to en if missing
            
            if lang == 'en':
                shutil.copy2(file_path, dest_dir / file_path.name)
                count += 1
                
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")
            
    print("\n" + "="*50)
    print("EXTRACTION COMPLETE")
    print("="*50)
    print(f"Total English Recipes Extracted: {count}")
    print(f"Destination: {dest_dir}")
    print("="*50)

if __name__ == "__main__":
    extract_english_recipes()
