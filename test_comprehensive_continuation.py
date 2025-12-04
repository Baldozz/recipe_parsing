"""
Comprehensive test for context-aware continuation detection.
Tests three complex multi-page recipes: Rabbit, Colomba, Bloody Wong Tong.
"""

import json
from pathlib import Path
from src.parsers.jpeg_parser import parse_recipe_image


def find_recipe_images(base_name_pattern):
    """Find all images for a recipe based on filename pattern."""
    jpg_dir = Path("data/raw/jpg_recipes")
    all_images = sorted(jpg_dir.glob("*.jpg"))
    
    # Filter by pattern in filename
    matching = []
    for img in all_images:
        # Convert to lowercase for matching
        fname_lower = img.stem.lower()
        if any(pattern in fname_lower for pattern in base_name_pattern):
            matching.append(img)
    
    return matching


def test_recipe_group(recipe_name, image_patterns):
    """Test a group of images that should form one recipe."""
    print(f"\n{'='*70}")
    print(f"TESTING: {recipe_name}")
    print(f"{'='*70}")
    
    images = find_recipe_images(image_patterns)
    
    if not images:
        print(f"⚠ No images found for patterns: {image_patterns}")
        return []
    
    print(f"Found {len(images)} images:")
    for img in images:
        print(f"  - {img.name}")
    
    previous_context = []
    all_recipes = []
    
    for i, img_path in enumerate(images, 1):
        print(f"\n--- IMAGE {i}/{len(images)}: {img_path.name} ---")
        if previous_context:
            print(f"Context: {previous_context[-1][:80]}...")
        
        recipes = parse_recipe_image(str(img_path), previous_context=previous_context)
        
        for recipe in recipes:
            print(f"✓ Extracted: {recipe['name']}")
            print(f"  Type: {recipe.get('recipe_type', 'N/A')}")
            print(f"  Ingredients: {len(recipe.get('ingredients', []))}, Steps: {len(recipe.get('steps', []))}")
            
            all_recipes.append({
                'name': recipe['name'],
                'type': recipe.get('recipe_type'),
                'source': img_path.name,
                'full_recipe': recipe
            })
            
            # Build context
            context_summary = f"Recipe: {recipe['name']}\nType: {recipe.get('recipe_type')}"
            previous_context.append(context_summary)
            if len(previous_context) > 5:
                previous_context.pop(0)
    
    # Analyze results
    print(f"\n{'='*70}")
    print(f"RESULTS FOR {recipe_name}")
    print(f"{'='*70}")
    
    base_names = set()
    for r in all_recipes:
        # Extract base name (before first parenthesis)
        base = r['name'].split('(')[0].strip()
        base_names.add(base.lower())
    
    if len(base_names) == 1:
        print(f"✓ All {len(all_recipes)} recipes correctly linked under: '{list(base_names)[0]}'")
    else:
        print(f"✗ Multiple base names found:")
        for base in base_names:
            count = sum(1 for r in all_recipes if base in r['name'].lower())
            print(f"  - '{base}': {count} recipes")
    
    for r in all_recipes:
        suffix = ""
        if '(' in r['name']:
            suffix = f" {r['name'][r['name'].index('('):]}"
        print(f"  {r['source']}: {r['type']}{suffix}")
    
    return all_recipes


def main():
    """Run comprehensive continuation test."""
    print("\n" + "="*70)
    print("COMPREHENSIVE CONTEXT-AWARE CONTINUATION TEST")
    print("="*70)
    
    # Test 1: Rabbit and pork dumpling
    rabbit_results = test_recipe_group(
        "Rabbit and Pork Dumpling",
        ["rabbit", "jade"]
    )
    
    # Test 2: Colomba
    colomba_results = test_recipe_group(
        "Colomba",
        ["colomb"]
    )
    
    # Test 3: Bloody Wong Tong
    wong_results = test_recipe_group(
        "Bloody Wong Tong",
        ["wong", "beetroot"]
    )
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Rabbit recipes extracted: {len(rabbit_results)}")
    print(f"Colomba recipes extracted: {len(colomba_results)}")
    print(f"Wong Tong recipes extracted: {len(wong_results)}")
    print(f"Total: {len(rabbit_results) + len(colomba_results) + len(wong_results)} recipes")


if __name__ == "__main__":
    main()
