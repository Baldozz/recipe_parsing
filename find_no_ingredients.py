import json
from pathlib import Path

MERGED_DIR = "data/merged_llm"

def find_no_ingredients():
    path = Path(MERGED_DIR)
    files = list(path.glob("*.json"))
    
    no_ingredients = []
    
    print(f"Scanning {len(files)} files in {MERGED_DIR}...\n")
    
    for p in files:
        try:
            with open(p, 'r') as f:
                data = json.load(f)
            
            ingredients = data.get('ingredients', [])
            if not ingredients:
                no_ingredients.append(p)
        except Exception as e:
            print(f"Error reading {p}: {e}")

    print(f"Found {len(no_ingredients)} recipes without ingredients.")
    
    if no_ingredients:
        print("\nSample of recipes without ingredients:")
        for p in no_ingredients[:10]:
            print(f"- {p.name}")
            
        # Print content of the first one as a sample
        print(f"\n--- Content of {no_ingredients[0].name} ---")
        with open(no_ingredients[0], 'r') as f:
            print(json.dumps(json.load(f), indent=2))

if __name__ == "__main__":
    find_no_ingredients()
