import json
import os
import shutil
from pathlib import Path

def cleanup_dataset(data_dir: str = "data/parsed"):
    print(f"Cleaning dataset in {data_dir}...")
    
    parsed_dir = Path(data_dir)
    merged_dir = parsed_dir / "merged"
    merge_report_path = merged_dir / "_merge_report.json"
    
    trash_dir = parsed_dir / "trash"
    incomplete_dir = parsed_dir / "incomplete"
    
    os.makedirs(trash_dir, exist_ok=True)
    os.makedirs(incomplete_dir, exist_ok=True)
    
    # 1. Identify files to remove (merged parts)
    files_to_remove = set()
    if merge_report_path.exists():
        with open(merge_report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            for entry in report:
                for source_file in entry.get("source_files", []):
                    files_to_remove.add(source_file)
    
    print(f"Found {len(files_to_remove)} merged parts to remove.")

    stats = {
        "deleted": 0,
        "moved_to_trash": 0,
        "moved_to_incomplete": 0
    }
    
    all_files = list(parsed_dir.glob("*.json"))
    
    for file_path in all_files:
        if file_path.name.startswith("_"): 
            continue
            
        # 1. Delete redundant merged parts
        if file_path.name in files_to_remove:
            print(f"Deleting redundant: {file_path.name}")
            file_path.unlink()
            stats["deleted"] += 1
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            name = data.get("name", "").lower()
            
            # 2. Move empty or unknown to trash
            if (not ingredients and not steps) or "unknown" in name or "recipe" == name:
                print(f"Moving to trash: {file_path.name}")
                shutil.move(str(file_path), str(trash_dir / file_path.name))
                stats["moved_to_trash"] += 1
                continue
                
            # 3. Move incomplete to incomplete folder
            if not ingredients or not steps:
                print(f"Moving to incomplete: {file_path.name}")
                shutil.move(str(file_path), str(incomplete_dir / file_path.name))
                stats["moved_to_incomplete"] += 1
                continue
                
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    print("\n" + "="*50)
    print("CLEANUP COMPLETE")
    print("="*50)
    print(f"Deleted (Redundant): {stats['deleted']}")
    print(f"Moved to Trash (Empty/Unknown): {stats['moved_to_trash']}")
    print(f"Moved to Incomplete: {stats['moved_to_incomplete']}")
    print("="*50)

if __name__ == "__main__":
    cleanup_dataset()
