import shutil
from pathlib import Path

DATA_DIR = Path("recipe_parsing/data")
PARSED_DIR = DATA_DIR / "parsed"
INCOMPLETE_DIR = DATA_DIR / "incomplete"

def restore_recipes():
    print("Restoring recipes from Incomplete to Parsed...")
    
    if not INCOMPLETE_DIR.exists():
        print("No incomplete directory found.")
        return

    count = 0
    for file_path in INCOMPLETE_DIR.rglob("*.json"):
        # Calculate relative path to maintain structure (e.g. images/english/foo.json)
        rel_path = file_path.relative_to(INCOMPLETE_DIR)
        target_path = PARSED_DIR / rel_path
        
        # Ensure parent dir exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(file_path), str(target_path))
        print(f"Restored: {rel_path}")
        count += 1
        
    print(f"\nSuccessfully restored {count} recipes.")
    
    # Optional: Remove empty incomplete dir
    # shutil.rmtree(INCOMPLETE_DIR) 

if __name__ == "__main__":
    restore_recipes()
