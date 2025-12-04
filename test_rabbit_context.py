"""Test context-aware continuation with Rabbit Dumpling images."""

import json
from pathlib import Path
from src.parsers.jpeg_parser import parse_recipe_image


def test_rabbit_with_context():
    """Simulate sequential processing with context."""
    
    images = [
        "data/raw/jpg_recipes/20190828_185128.jpg",  # Main recipe
        "data/raw/jpg_recipes/20190828_185200.jpg",  # To serve
        "data/raw/jpg_recipes/20190828_185219.jpg",  # Seasoning
    ]
    
    previous_context = []
    all_recipes = []
    
    for i, img_path in enumerate(images, 1):
        print(f"\n{'='*60}")
        print(f"IMAGE {i}: {Path(img_path).name}")
        print(f"{'='*60}")
        print(f"Context: {previous_context if previous_context else 'None'}\n")
        
        recipes = parse_recipe_image(img_path, previous_context=previous_context)
        
        for recipe in recipes:
            print(f"Extracted: {recipe['name']}")
            print(f"Type: {recipe.get('recipe_type', 'N/A')}")
            print(f"Ingredients: {len(recipe.get('ingredients', []))} items")
            print(f"Steps: {len(recipe.get('steps', []))} items\n")
            
            all_recipes.append(recipe)
            
            # Build context for next image
            context_summary = f"Recipe: {recipe['name']}\nType: {recipe.get('recipe_type')}"
            previous_context.append(context_summary)
            
            # Keep only last 5
            if len(previous_context) > 5:
                previous_context.pop(0)
    
    # Check if they're named as continuations
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")
    
    for recipe in all_recipes:
        print(f"\n{recipe['name']} ({recipe.get('recipe_type')})")
    
    # Expected: All should have "Rabbit and pork dumpling" in the name
    base_name = "Rabbit and pork dumpling"
    correctly_named = all(base_name.lower() in r['name'].lower() for r in all_recipes)
    
    if correctly_named:
        print(f"\n✓ All recipes correctly linked to '{base_name}'")
    else:
        print(f"\n✗ Some recipes not linked to '{base_name}'")
        for r in all_recipes:
            if base_name.lower() not in r['name'].lower():
                print(f"  - '{r['name']}' is standalone (should be continuation)")


if __name__ == "__main__":
    test_rabbit_with_context()
