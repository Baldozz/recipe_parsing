import json
from pathlib import Path

def show_partial_samples(data_dir: str = "data/english_recipes", limit: int = 3):
    p = Path(data_dir)
    partial_files = []
    
    for f in p.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                
            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            
            if not ingredients or not steps:
                partial_files.append(f)
                if len(partial_files) >= limit:
                    break
        except:
            pass
            
    print(f"Found {len(partial_files)} partial samples (stopping at {limit}):\n")
    
    for f in partial_files:
        print(f"File: {f.name}")
        print("-" * 20)
        with open(f, "r", encoding="utf-8") as file:
            print(file.read())
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    show_partial_samples()
