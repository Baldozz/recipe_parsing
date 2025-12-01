import os
from pathlib import Path

def cleanup_english_recipes(data_dir: str = "data/english_recipes"):
    print(f"Cleaning up redundant parts in {data_dir}...")
    
    data_path = Path(data_dir)
    files = list(data_path.glob("*.json"))
    
    # Identify merged files and their base names
    merged_bases = set()
    for f in files:
        if f.name.endswith("_merged.json"):
            # Extract base name: "recipe_name_merged.json" -> "recipe_name"
            base = f.name.replace("_merged.json", "")
            merged_bases.add(base)
            
    print(f"Found {len(merged_bases)} merged recipes.")
    
    deleted_count = 0
    
    for f in files:
        # Skip the merged files themselves
        if f.name.endswith("_merged.json"):
            continue
            
        # Check if this file belongs to a merged base
        for base in merged_bases:
            # Check if file starts with base name
            if f.name.startswith(base):
                # Ensure it's actually a match and not just a prefix of another recipe
                # Valid suffixes after base: _part_X, _parsed, _en_parsed, etc.
                # We want to delete parts and partials
                
                remainder = f.name[len(base):]
                
                # Check for "part" files
                if "_part_" in remainder:
                    print(f"Deleting redundant part: {f.name} (covered by {base}_merged.json)")
                    f.unlink()
                    deleted_count += 1
                    break
                    
                # Check for exact base matches that might be partials (e.g. recipe_parsed.json vs recipe_merged.json)
                # But be careful not to delete distinct recipes.
                # If we have "recipe_merged.json", usually "recipe_parsed.json" was one of the parts (the main one).
                
                if remainder in ["_parsed.json", "_en_parsed.json", "_es_parsed.json", "_it_parsed.json", "_fr_parsed.json"]:
                     print(f"Deleting redundant base: {f.name} (covered by {base}_merged.json)")
                     f.unlink()
                     deleted_count += 1
                     break
                     
                # Handle counters like _parsed_2.json
                if "_parsed_" in remainder and remainder.split("_parsed_")[-1].replace(".json", "").isdigit():
                     print(f"Deleting redundant variant: {f.name} (covered by {base}_merged.json)")
                     f.unlink()
                     deleted_count += 1
                     break

    print("\n" + "="*50)
    print("ENGLISH CLEANUP COMPLETE")
    print("="*50)
    print(f"Total Files Deleted: {deleted_count}")
    print("="*50)

if __name__ == "__main__":
    cleanup_english_recipes()
