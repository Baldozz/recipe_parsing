import os
import json
import shutil
from pathlib import Path
from src.parsers.jpeg_parser import parse_recipe_image
from src.stitch_recipes import stitch_recipes

def test_colomba():
    print("=== Testing Context-Aware Parsing on Colomba ===")
    
    # Setup paths
    # Order: Rinfresco -> 1st Impasto -> 2nd Impasto
    img1 = "data/raw/test_colomba_images/colomba_1_rinfresco.jpg"
    img2 = "data/raw/test_colomba_images/colomba_2_impasto1.jpg"
    img3 = "data/raw/test_colomba_images/colomba_3_impasto2.jpg"
    
    output_dir = "data/parsed_test_colomba"
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # 1. Parse Image 1 (Rinfresco)
    print(f"\nParsing Part 1: {img1}")
    recipes1 = parse_recipe_image(img1, previous_context=[])
    
    if not recipes1:
        print("Failed to parse Image 1")
        return

    r1 = recipes1[0]
    name1 = r1.get("name")
    print(f"Result 1 Name: '{name1}'")
    
    # Save Part 1
    with open(f"{output_dir}/colomba_part1.json", "w") as f:
        json.dump(r1, f, indent=2)
        
    # Prepare Context 1
    context_summary1 = f"Recipe: {name1}\nIngredients: {', '.join(r1.get('ingredients', [])[:5])}..."
    previous_context = [context_summary1]
    
    # 2. Parse Image 2 (1st Impasto)
    print(f"\nParsing Part 2: {img2}")
    print(f"Context provided: {previous_context}")
    
    recipes2 = parse_recipe_image(img2, previous_context=previous_context)
    
    if not recipes2:
        print("Failed to parse Image 2")
        return

    r2 = recipes2[0]
    name2 = r2.get("name")
    print(f"Result 2 Name: '{name2}'")
    
    # Save Part 2
    with open(f"{output_dir}/colomba_part2.json", "w") as f:
        json.dump(r2, f, indent=2)

    # Prepare Context 2
    context_summary2 = f"Recipe: {name2}\nIngredients: {', '.join(r2.get('ingredients', [])[:5])}..."
    previous_context.append(context_summary2)

    # 3. Parse Image 3 (2nd Impasto)
    print(f"\nParsing Part 3: {img3}")
    print(f"Context provided: {previous_context}")
    
    recipes3 = parse_recipe_image(img3, previous_context=previous_context)
    
    if not recipes3:
        print("Failed to parse Image 3")
        return

    r3 = recipes3[0]
    name3 = r3.get("name")
    print(f"Result 3 Name: '{name3}'")
    
    # Save Part 3
    with open(f"{output_dir}/colomba_part3.json", "w") as f:
        json.dump(r3, f, indent=2)
        
    # 4. Run Stitching
    print("\nRunning Stitcher...")
    stitch_recipes(output_dir)
    
    # 4. Verify Result
    files = list(Path(output_dir).glob("*.json"))
    print(f"\nFiles in output dir: {[f.name for f in files]}")
    
    # We expect 'colombe_parsed.json' (base name)
    
    for f in files:
        with open(f, "r") as f_in:
            data = json.load(f_in)
            print(f"\nChecking {f.name}:")
            print(f"Name: {data.get('name')}")
            print(f"Ingredients count: {len(data.get('ingredients', []))}")
            print(f"Steps count: {len(data.get('steps', []))}")
            
            # Check for source_files
            sources = data.get("other_details", {}).get("source_files", [])
            print(f"Source Files: {json.dumps(sources, indent=2)}")
            
            # Check for headers
            ingredients = data.get("ingredients", [])
            headers = [i for i in ingredients if i.startswith("##")]
            print(f"Ingredient Headers: {headers}")

if __name__ == "__main__":
    test_colomba()
