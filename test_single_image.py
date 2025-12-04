"""Test single image parsing with updated rules."""
from src.parsers.jpeg_parser import parse_recipe_image
import json

# Parse Kow Choi Oil image
print("Parsing Kow Choi Oil with updated rules...")
recipes = parse_recipe_image("data/raw/jpg_recipes/20190828_183536.jpg")

print(f"\nFound {len(recipes)} recipe(s)\n")

for recipe in recipes:
    print(json.dumps(recipe, indent=2, ensure_ascii=False))
    
    # Verification
    print("\n=== VERIFICATION ===")
    
    # Check ingredients
    olive_oil = [ing for ing in recipe.get('ingredients', []) if 'olive' in ing.lower()]
    if olive_oil:
        print(f"Olive Oil: {olive_oil[0]}")
        if "200100" in olive_oil[0]:
            print("❌ FAIL: Still concatenating crossed-out text")
        elif "200" in olive_oil[0] and "100" not in olive_oil[0]:
            print("✅ PASS: Handwritten 200g used")
        else:
            print("⚠️  Check: ", olive_oil[0])
    
    # Check steps
    steps_str = " ".join(recipe.get('steps', []))
    if "lemon oil" in steps_str.lower():
        print("❌ FAIL: 'lemon oil' still in steps (should be excluded)")
    else:
        print("✅ PASS: 'lemon oil' excluded from steps")
    
    # Check related_to
    if recipe.get('related_to'):
        print(f"✅ PASS: related_to = '{recipe['related_to']}'")
    else:
        print("❌ FAIL: related_to is null (should be 'Taro Dumpling')")
    
    # Check Chinese
    notes = recipe.get('other_details', {}).get('notes', '')
    if any('\u4e00' <= c <= '\u9fff' for c in notes):
        print("❌ FAIL: Chinese characters still in notes")
    else:
        print("✅ PASS: No Chinese characters in notes")
