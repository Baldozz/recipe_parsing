"""
Simplified test using exact known filenames for Rabbit, Colomba, and Bloody Wong Tong.
"""

import json
from pathlib import Path
from src.parsers.jpeg_parser import parse_recipe_image


def test_recipe_sequence(recipe_name, image_files):
    """Test a sequence of images that should form one recipe."""
    print(f"\n{'='*70}")
    print(f"TESTING: {recipe_name}")
    print(f"{'='*70}")
    
    # Check which images exist
    jpg_dir = Path("data/raw/jpg_recipes")
    existing_images = []
    for fname in image_files:
        img_path = jpg_dir / fname
        if img_path.exists():
            existing_images.append(img_path)
        else:
            print(f"⚠ Image not found: {fname}")
    
    if not existing_images:
        print(f"✗ No images found for {recipe_name}")
        return []
    
    print(f"Found {len(existing_images)}/{len(image_files)} images\n")
    
    previous_context = []
    all_recipes = []
    
    for i, img_path in enumerate(existing_images, 1):
        print(f"--- IMAGE {i}/{len(existing_images)}: {img_path.name} ---")
        
        recipes = parse_recipe_image(str(img_path), previous_context=previous_context)
        
        for recipe in recipes:
            print(f"✓ {recipe['name']}")
            print(f"  Type: {recipe.get('recipe_type')}")
            print(f"  Content: {len(recipe.get('ingredients', []))} ingredients, {len(recipe.get('steps', []))} steps\n")
            
            all_recipes.append({
                'name': recipe['name'],
                'type': recipe.get('recipe_type'),
                'source': img_path.name
            })
            
            # Build context
            context_summary = f"Recipe: {recipe['name']}\nType: {recipe.get('recipe_type')}"
            previous_context.append(context_summary)
            if len(previous_context) > 5:
                previous_context.pop(0)
    
    # Verify continuation linking
    print(f"{'='*70}")
    print(f"VERIFICATION: {recipe_name}")
    print(f"{'='*70}")
    
    # Check if all recipes share the same base name
    base_names = set()
    for r in all_recipes:
        base = r['name'].split('(')[0].strip()
        base_names.add(base.lower())
    
    if len(base_names) == 1:
        print(f"✓ SUCCESS: All {len(all_recipes)} parts correctly linked")
        print(f"  Base name: '{list(base_names)[0]}'")
    else:
        print(f"✗ FAILED: Found {len(base_names)} different base names:")
        for base in sorted(base_names):
            count = sum(1 for r in all_recipes if base in r['name'].lower())
            print(f"  - '{base}': {count} parts")
    
    print("\nExtracted parts:")
    for r in all_recipes:
        print(f"  {r['source']}: {r['name']} ({r['type']})")
    
    return all_recipes


def main():
    print("\n" + "="*70)
    print("COMPREHENSIVE CONTINUATION TEST - Known Image Files")
    print("="*70)
    
    # Test 1: Rabbit and Pork Dumpling (we know these exist from metadata)
    rabbit_results = test_recipe_sequence(
        "Rabbit and Pork Dumpling",
        [
            "20190828_185128.jpg",  # Main recipe
            "20190828_185200.jpg",  # To serve
            "20190828_185219.jpg",  # Seasoning
        ]
    )
    
    # Test 2: Bloody Wong Tong (from your uploaded images)
    wong_results = test_recipe_sequence(
        "Bloody Wong Tong",
        [
            "bloody_wong_tong_page1.jpg",  # We copied this earlier
            "bloody_wong_tong_page2.jpg",
        ]
    )
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"✓ Rabbit recipes: {len(rabbit_results)} parts extracted")
    print(f"✓ Wong Tong recipes: {len(wong_results)} parts extracted")
    print(f"\nTotal: {len(rabbit_results) + len(wong_results)} recipe parts")
    
    # Check overall success
    all_results = rabbit_results + wong_results
    if all_results:
        print(f"\n{len([r for r in all_results if r['type'] in ['main', 'component', 'preparation']])} content recipes")
        print(f"{len([r for r in all_results if r['type'] == 'assembly'])} assembly sections")


if __name__ == "__main__":
    main()
