import json
from pathlib import Path
import statistics

def check_english_quality(data_dir: str = "data/english_recipes"):
    print(f"Checking quality of recipes in {data_dir}...")
    
    p = Path(data_dir)
    if not p.exists():
        print(f"Directory {data_dir} does not exist.")
        return

    files = list(p.glob("*.json"))
    total_files = len(files)
    
    full_recipes = []
    partial_recipes = []
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                
            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            
            if ingredients and steps:
                full_recipes.append(f.name)
            else:
                partial_recipes.append(f.name)
                
        except Exception as e:
            print(f"Error reading {f.name}: {e}")

    print("\n" + "="*50)
    print("ENGLISH RECIPES QUALITY REPORT")
    print("="*50)
    print(f"Total Files: {total_files}")
    print(f"High Quality (Ingredients + Steps): {len(full_recipes)} ({len(full_recipes)/total_files*100:.1f}%)")
    print(f"Partial (Missing Ingredients or Steps): {len(partial_recipes)} ({len(partial_recipes)/total_files*100:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    check_english_quality()
