"""Test single image parsing with updated rules for Rabbit recipe."""
from src.parsers.jpeg_parser import parse_recipe_image
import json

# Rabbit and pork dumpling image
image_path = "data/raw/jpg_recipes/20190828_184807.jpg"

print(f"Parsing Rabbit recipe ({image_path}) with updated rules...")
try:
    recipes = parse_recipe_image(image_path)
    print(f"\nFound {len(recipes)} recipe(s)\n")

    for recipe in recipes:
        print(json.dumps(recipe, indent=2, ensure_ascii=False))
        
        # Verification
        print("\n=== VERIFICATION ===")
        print(f"Name: {recipe.get('name')}")
        print(f"Type: {recipe.get('recipe_type')}")
        
        # Check parsing analysis
        analysis = recipe.get('_parsing_analysis', {})
        print("Parsing Analysis:", json.dumps(analysis, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"Error: {e}")
