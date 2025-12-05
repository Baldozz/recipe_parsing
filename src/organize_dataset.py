import json
import shutil
from pathlib import Path

DATA_DIR = Path("recipe_parsing/data")
PARSED_DIR = DATA_DIR / "parsed"
INCOMPLETE_DIR = DATA_DIR / "incomplete"
TRASH_DIR = DATA_DIR / "trash"

def organize_recipes():
    print("Organizing recipes into Incomplete and Trash folders...")
    
    INCOMPLETE_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    
    count_moved_incomplete = 0
    count_moved_trash = 0
    
    for file_path in PARSED_DIR.rglob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Criteria for Trash
            if not data or (not data.get('ingredients') and not data.get('steps') and not data.get('name')):
                target_dir = TRASH_DIR / file_path.parent.relative_to(PARSED_DIR)
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_dir / file_path.name))
                print(f"Moved to Trash: {file_path.name}")
                count_moved_trash += 1
                continue

            # Criteria for Incomplete
            # If it has a name but missing BOTH ingredients and steps, or just very sparse
            has_ingredients = bool(data.get('ingredients'))
            has_steps = bool(data.get('steps'))
            
            if not has_ingredients or not has_steps:
                target_dir = INCOMPLETE_DIR / file_path.parent.relative_to(PARSED_DIR)
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_dir / file_path.name))
                print(f"Moved to Incomplete: {file_path.name}")
                count_moved_incomplete += 1
                continue
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print(f"\nSummary:")
    print(f"Moved {count_moved_incomplete} recipes to {INCOMPLETE_DIR}")
    print(f"Moved {count_moved_trash} recipes to {TRASH_DIR}")

if __name__ == "__main__":
    organize_recipes()
