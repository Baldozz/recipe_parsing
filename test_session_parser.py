import sys
import os
import json
sys.path.append(os.getcwd())

from src.parsers.session_parser import parse_recipe_session

def test_mugaritz():
    # Mugaritz Sweetbreads (Main + Finishing)
    images = [
        "data/raw/jpg_recipes/IMG_1495.JPG",
        "data/raw/jpg_recipes/IMG_1496.JPG"
    ]
    
    print(f"Testing Session Parser on: {images}")
    
    recipes = parse_recipe_session(images)
    
    print(f"\nFound {len(recipes)} recipes.")
    for r in recipes:
        print(f"\n--- Recipe: {r.get('name')} ---")
        print(f"Type: {r.get('recipe_type')}")
        print(f"Source Files: {r.get('source_files')}")
        print(f"Ingredients: {len(r.get('ingredients', []))}")
        print(f"Steps: {len(r.get('steps', []))}")
        
        # Check for "Finishing" content
        has_finishing = any("finish" in s.lower() for s in r.get('ingredients', []) + r.get('steps', []))
        print(f"Has 'Finishing' content? {has_finishing}")

if __name__ == "__main__":
    test_mugaritz()
