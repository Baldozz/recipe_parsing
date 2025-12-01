import json
import os
from pathlib import Path
from collections import defaultdict

def analyze_dataset(data_dir: str = "data/parsed"):
    print(f"Analyzing dataset in {data_dir}...")
    
    parsed_dir = Path(data_dir)
    merged_dir = parsed_dir / "merged"
    merge_report_path = merged_dir / "_merge_report.json"
    
    # 1. Identify files to remove (merged parts)
    files_to_remove = set()
    if merge_report_path.exists():
        with open(merge_report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            for entry in report:
                for source_file in entry.get("source_files", []):
                    files_to_remove.add(source_file)
    
    print(f"Found {len(files_to_remove)} files that have been merged and can be removed.")

    # 2. Scan all files
    stats = {
        "total_files": 0,
        "merged_files": 0,
        "redundant_files": 0,
        "incomplete_recipes": [],
        "unknown_recipes": [],
        "empty_files": []
    }
    
    all_files = list(parsed_dir.glob("*.json")) + list(merged_dir.glob("*.json"))
    
    for file_path in all_files:
        if file_path.name.startswith("_"): # Skip reports
            continue
            
        stats["total_files"] += 1
        
        # Check if it's a merged file
        if "merged" in file_path.name:
            stats["merged_files"] += 1
            
        # Check if it's redundant
        if file_path.name in files_to_remove:
            stats["redundant_files"] += 1
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Check for incomplete
                ingredients = data.get("ingredients", [])
                steps = data.get("steps", [])
                name = data.get("name", "").lower()
                
                if not ingredients and not steps:
                    stats["empty_files"].append(file_path.name)
                elif not ingredients or not steps:
                    stats["incomplete_recipes"].append({
                        "file": file_path.name,
                        "missing": "ingredients" if not ingredients else "steps"
                    })
                    
                # Check for unknown
                if "unknown" in name or "recipe" == name:
                    stats["unknown_recipes"].append(file_path.name)
                    
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    # 3. Print Report
    print("\n" + "="*50)
    print("DATASET ANALYSIS REPORT")
    print("="*50)
    print(f"Total JSON Files: {stats['total_files']}")
    print(f"Merged Recipes: {stats['merged_files']}")
    print(f"Redundant Parts (Safe to Delete): {stats['redundant_files']}")
    print("-" * 30)
    print(f"Empty Files (No ingredients/steps): {len(stats['empty_files'])}")
    print(f"Incomplete Recipes (Missing one): {len(stats['incomplete_recipes'])}")
    print(f"Unknown/Generic Names: {len(stats['unknown_recipes'])}")
    print("="*50)
    
    if stats["empty_files"]:
        print("\nEmpty Files Sample:")
        for f in stats["empty_files"][:5]:
            print(f"  - {f}")
            
    if stats["incomplete_recipes"]:
        print("\nIncomplete Recipes Sample:")
        for item in stats["incomplete_recipes"][:5]:
            print(f"  - {item['file']} (Missing: {item['missing']})")

    if stats["unknown_recipes"]:
        print("\nUnknown Recipes Sample:")
        for f in stats["unknown_recipes"][:5]:
            print(f"  - {f}")

if __name__ == "__main__":
    analyze_dataset()
