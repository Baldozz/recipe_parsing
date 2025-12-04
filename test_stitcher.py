"""Test the stitcher with Bloody Wong Tong recipes."""

import json
import shutil
from pathlib import Path
from src.stitch_recipes import stitch_recipes

def setup_test_files():
    """Create test parsed directory with Bloody Wong Tong recipes."""
    test_dir = Path("data/test_stitch")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the extracted recipes
    with open("bloody_wong_tong_test_output.json") as f:
        recipes = json.load(f)
    
    # Save each as separate parsed file
    for i, recipe in enumerate(recipes, 1):
        name = recipe['name'].lower().replace(' ', '_').replace('/', '_')
        filename = f"{name}_parsed.json"
        
        with open(test_dir / filename, 'w') as f:
            json.dump(recipe, f, indent=2)
        
        print(f"Created: {filename}")
    
    return test_dir

def main():
    print("=" * 60)
    print("SETTING UP TEST FILES")
    print("=" * 60)
    
    test_dir = setup_test_files()
    output_dir = Path("data/test_stitch_output")
    
    print("\n" + "=" * 60)
    print("RUNNING STITCHER")
    print("=" * 60)
    
    result = stitch_recipes(str(test_dir), str(output_dir))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for filename in sorted(output_dir.glob("*.json")):
        with open(filename) as f:
            recipe = json.load(f)
        
        print(f"\nFile: {filename.name}")
        print(f"  Name: {recipe.get('name')}")
        print(f"  Type: {recipe.get('recipe_type', 'N/A')}")
        print(f"  Ingredients: {len(recipe.get('ingredients', []))} items")
        print(f"  Steps: {len(recipe.get('steps', []))} items")
        
        # Check for "To Serve" header
        if "## To Serve" in recipe.get('steps', []):
            print(f"  ✓ Assembly section merged!")

if __name__ == "__main__":
    main()
