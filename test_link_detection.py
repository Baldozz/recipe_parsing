"""Test global link detection with Taro recipe chain."""

import json
from pathlib import Path
from src.parsers.jpeg_parser import parse_recipe_image
from src.stitch_recipes import stitch_recipes
from src.link_recipes import detect_links


def create_taro_test_recipes():
    """Create test Taro recipes to verify linking."""
    test_dir = Path("data/test_taro")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock Taro Puree
    puree = {
        "name": "Taro Puree",
        "recipe_type": "component",
        "ingredients": ["6 kg Taro", "Water"],
        "steps": ["Peel and dice taro", "Boil until soft"],
        "other_details": {}
    }
    
    # Mock Taro Dough (uses Taro Puree)
    dough = {
        "name": "Taro Dough",
        "recipe_type": "component",
        "ingredients": [
            "300 g Taro Puree",  # <- Should link to "Taro Puree"
            "170 g Tapioca Powder",
            "70 g Water"
        ],
        "steps": ["Mix taro puree and tapioca", "Add water"],
        "other_details": {}
    }
    
    # Mock Taro Dumpling (uses Taro Dough)
    dumpling = {
        "name": "Taro Dumpling",
        "recipe_type": "main",
        "ingredients": [
            "15 g Taro Dough",  # <- Should link to "Taro Dough"
            "8 g Taiwanese sausage"
        ],
        "steps": ["Fold", "Steam for 2.5min"],
        "other_details": {}
    }
    
    # Save test files
    with open(test_dir / "taro_puree_parsed.json", 'w') as f:
        json.dump(puree, f, indent=2)
    
    with open(test_dir / "taro_dough_parsed.json", 'w') as f:
        json.dump(dough, f, indent=2)
    
    with open(test_dir / "taro_dumpling_parsed.json", 'w') as f:
        json.dump(dumpling, f, indent=2)
    
    print("Created 3 test Taro recipes\n")
    return test_dir


def main():
    print("=" * 60)
    print("PHASE 3: GLOBAL LINK DETECTION TEST")
    print("=" * 60)
    
    # Create test recipes
    test_dir = create_taro_test_recipes()
    output_dir = Path("data/test_taro_linked")
    
    # Run link detection
    print("\nRunning link detection...")
    print("=" * 60)
    linked_recipes = detect_links(str(test_dir), str(output_dir))
    
    # Verify results
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    for filename in sorted(output_dir.glob("*.json")):
        with open(filename) as f:
            recipe = json.load(f)
        
        print(f"\n{recipe['name']}:")
        print(f"  Type: {recipe.get('recipe_type')}")
        
        if 'requires' in recipe:
            print(f"  Requires: {recipe['requires']}")
        
        if 'used_in' in recipe:
            print(f"  Used in: {recipe['used_in']}")
    
    # Expected results
    print("\n" + "=" * 60)
    print("EXPECTED DEPENDENCY CHAIN:")
    print("=" * 60)
    print("Taro Puree → Taro Dough → Taro Dumpling")
    print("\nTaro Puree:")
    print("  used_in: ['Taro Dough']")
    print("\nTaro Dough:")
    print("  requires: ['Taro Puree']")
    print("  used_in: ['Taro Dumpling']")
    print("\nTaro Dumpling:")
    print("  requires: ['Taro Dough']")


if __name__ == "__main__":
    main()
