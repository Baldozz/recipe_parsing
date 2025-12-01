import json
import shutil
from pathlib import Path

def move_partial_recipes(source_dir: str = "data/english_recipes", dest_dir: str = "data/parsed/incomplete"):
    print(f"Moving partial recipes from {source_dir} to {dest_dir}...")
    
    src = Path(source_dir)
    dst = Path(dest_dir)
    
    if not src.exists():
        print(f"Source directory {source_dir} does not exist.")
        return

    # Create destination directory if it doesn't exist
    dst.mkdir(parents=True, exist_ok=True)
    
    files = list(src.glob("*.json"))
    moved_count = 0
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                
            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            
            # Check if partial (missing ingredients OR missing steps)
            if not ingredients or not steps:
                shutil.move(str(f), str(dst / f.name))
                moved_count += 1
                print(f"Moved: {f.name}")
                
        except Exception as e:
            print(f"Error processing {f.name}: {e}")

    print("\n" + "="*50)
    print("MOVE COMPLETE")
    print("="*50)
    print(f"Total Files Moved: {moved_count}")
    print(f"Remaining High Quality Files: {len(list(src.glob('*.json')))}")
    print("="*50)

if __name__ == "__main__":
    move_partial_recipes()
