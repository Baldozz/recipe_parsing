"""
Phase 3: Global Link Detection

Scans all recipes in the dataset to find component relationships.
Builds 'requires' and 'used_in' arrays to create dependency graph.
"""

import json
from pathlib import Path
from collections import defaultdict


def normalize_name(name: str) -> str:
    """Normalize recipe name for matching."""
    return name.lower().strip()


def detect_links(input_dir: str, output_dir: str):
    """
    Scan all recipes to detect component relationships.
    
    Args:
        input_dir: Directory with stitched recipes
        output_dir: Where to save linked recipes
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load all recipes
    recipes = {}
    for file_path in sorted(input_path.rglob("*.json")):
        with open(file_path, 'r') as f:
            recipe = json.load(f)
            recipes[file_path.stem] = recipe
    
    print(f"Scanning {len(recipes)} recipes for component links...\n")
    
    # Build name index for fast lookup
    name_to_filename = {}
    for filename, recipe in recipes.items():
        name_to_filename[normalize_name(recipe['name'])] = filename
    
    # Detect links
    links_found = 0
    for filename, recipe in recipes.items():
        requires = []
        
        # Search ingredients for other recipe names
        for ingredient in recipe.get('ingredients', []):
            if isinstance(ingredient, dict):
                ingredient_text = ingredient.get('name', '')
            else:
                ingredient_text = str(ingredient)
                
            ingredient_lower = ingredient_text.lower()
            
            # Skip headers
            if ingredient_text.startswith('##'):
                continue
            
            # Check if any other recipe name appears in this ingredient
            for other_name, other_filename in name_to_filename.items():
                if other_filename == filename:
                    continue  # Don't link to self
                
                # Check for name match (must be whole word to avoid false positives)
                if other_name in ingredient_lower:
                    # Verify it's a word boundary match
                    import re
                    pattern = r'\b' + re.escape(other_name) + r'\b'
                    if re.search(pattern, ingredient_lower):
                        requires.append(recipes[other_filename]['name'])
                        links_found += 1
                        print(f"  '{recipe['name']}' requires '{recipes[other_filename]['name']}'")
        
        # Add requires array if any found
        if requires:
            recipe['requires'] = list(set(requires))  # Remove duplicates
    
    # Build reverse links (used_in)
    for filename, recipe in recipes.items():
        used_in = []
        
        for other_filename, other_recipe in recipes.items():
            if other_filename == filename:
                continue
            
            # Check if this recipe is in the other's requires
            if recipe['name'] in other_recipe.get('requires', []):
                used_in.append(other_recipe['name'])
        
        if used_in:
            recipe['used_in'] = list(set(used_in))
    
    # Save linked recipes
    for filename, recipe in recipes.items():
        output_file = output_path / f"{filename}.json"
        with open(output_file, 'w') as f:
            json.dump(recipe, f, indent=2)
    
    print(f"\nLink detection complete.")
    print(f"Found {links_found} component relationships.")
    
    # Print summary of recipes with links
    linked_count = sum(1 for r in recipes.values() if 'requires' in r or 'used_in' in r)
    print(f"{linked_count}/{len(recipes)} recipes have component relationships.")
    
    return recipes


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 link_recipes.py <input_dir> <output_dir>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    detect_links(input_dir, output_dir)
