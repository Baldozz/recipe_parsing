import json
from src.parsers.jpeg_parser import parse_recipe_image

def test_bloody_wong_tong():
    print("=" * 60)
    print("TESTING BLOODY WONG TONG - PAGE 1")
    print("=" * 60)
    
    recipes_page1 = parse_recipe_image("data/raw/bloody_wong_tong_page1.jpg", previous_context=[])
    
    print("\n--- PAGE 1 RESULTS ---\n")
    for i, r in enumerate(recipes_page1, 1):
        print(f"\nRecipe {i}:")
        print(f"  Name: {r.get('name')}")
        print(f"  Type: {r.get('recipe_type', 'NOT SET')}")
        print(f"  Ingredients: {len(r.get('ingredients', []))} items")
        print(f"  Steps: {len(r.get('steps', []))} items")
    
    # Build context for page 2
    context = [
        f"Recipe: {r.get('name')}\nType: {r.get('recipe_type')}\nIngredients: {', '.join(r.get('ingredients', [])[:3])}..."
        for r in recipes_page1
    ]
    
    print("\n" + "=" * 60)
    print("TESTING BLOODY WONG TONG - PAGE 2")
    print("=" * 60)
    
    recipes_page2 = parse_recipe_image("data/raw/bloody_wong_tong_page2.jpg", previous_context=context)
    
    print("\n--- PAGE 2 RESULTS ---\n")
    for i, r in enumerate(recipes_page2, 1):
        print(f"\nRecipe {i}:")
        print(f"  Name: {r.get('name')}")
        print(f"  Type: {r.get('recipe_type', 'NOT SET')}")
        print(f"  Ingredients: {len(r.get('ingredients', []))} items")
        print(f"  Steps: {len(r.get('steps', []))} items")
    
    # Save full output for inspection
    all_recipes = recipes_page1 + recipes_page2
    with open("bloody_wong_tong_test_output.json", "w") as f:
        json.dump(all_recipes, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"TOTAL EXTRACTED: {len(all_recipes)} recipes")
    print("Full output saved to: bloody_wong_tong_test_output.json")
    print("=" * 60)

if __name__ == "__main__":
    test_bloody_wong_tong()
