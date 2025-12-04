import sys
import os
import json
sys.path.append(os.getcwd())

from src.parsers.session_parser import parse_recipe_session

def test_sessions():
    test_cases = [
        {
            "name": "Reverse Order Test (IMG_2074/2075)",
            "images": ["data/raw/jpg_recipes/IMG_2074.JPG", "data/raw/jpg_recipes/IMG_2075.JPG"]
        }
    ]
    
    for case in test_cases:
        print(f"\n\n=== Testing: {case['name']} ===")
        print(f"Images: {case['images']}")
        
        try:
            recipes = parse_recipe_session(case['images'])
            
            print(f"Found {len(recipes)} recipes:")
            for r in recipes:
                print(f"  - Name: {r.get('name')}")
                print(f"    Type: {r.get('recipe_type')}")
                print(f"    Source Files: {r.get('source_files')}")
                print(f"    Ingredients: {len(r.get('ingredients', []))}")
                print(f"    Steps: {len(r.get('steps', []))}")
                
                # Check for merge indicators
                if len(r.get('source_files', [])) > 1:
                    print("    ✅ MERGED (Multiple sources)")
                else:
                    print("    ⚠️  NOT MERGED (Single source)")
                    
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_sessions()
