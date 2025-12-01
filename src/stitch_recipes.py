import json
import re
import shutil
from pathlib import Path
from collections import defaultdict
import argparse

def parse_part_info(name: str):
    """
    Detect if a name indicates a part of a recipe.
    Returns (base_name, part_number) or (None, None).
    """
    # Patterns to match:
    # "Recipe Name (Part 1)"
    # "Recipe Name Part 1"
    # "Recipe Name (1/2)"
    # "Recipe Name 1 of 2"
    
    # Normalize to lower case for matching
    lower_name = name.lower()
    
    # Pattern 1: (Part X) or Part X
    match = re.search(r"(.*?)\s*\(?part\s*(\d+)\)?", lower_name)
    if match:
        base = match.group(1).strip()
        part = int(match.group(2))
        return base, part
        
    # Pattern 2: (X/Y) or X/Y
    match = re.search(r"(.*?)\s*\(?(\d+)\s*/\s*(\d+)\)?", lower_name)
    if match:
        base = match.group(1).strip()
        part = int(match.group(2))
        return base, part

    # Pattern 3: (continued) or (cont) -> Treat as Part 2 if not specified
    # This is trickier as we might have Part 1 and then (cont).
    # For now, let's stick to explicit numbering or handle simple (cont) as part 2
    if "(cont" in lower_name or "(continued)" in lower_name:
        base = re.sub(r"\s*\(?cont(inued)?\)?\.?", "", lower_name).strip()
        return base, 2

    return None, None

def merge_recipes(parts: list) -> dict:
    """
    Merge a list of recipe parts into a single recipe.
    Parts should be sorted by part number.
    """
    if not parts:
        return None
        
    # Start with the first part
    merged = parts[0].copy()
    
    # Clean up the name (remove "Part 1" etc)
    # We use the base name derived from the first part's name logic
    base_name, _ = parse_part_info(merged.get("name", ""))
    if base_name:
        # Capitalize nicely (simple title case)
        merged["name"] = base_name.title() 
    
    all_ingredients = set(merged.get("ingredients", []))
    all_steps = merged.get("steps", [])
    
    for part in parts[1:]:
        # Merge ingredients (union)
        for ing in part.get("ingredients", []):
            all_ingredients.add(ing)
            
        # Append steps
        all_steps.extend(part.get("steps", []))
        
        # Merge other details (simple update, later parts override earlier)
        if "other_details" in part:
            if "other_details" not in merged:
                merged["other_details"] = {}
            merged["other_details"].update(part.get("other_details", {}))
            
        # Merge source metadata if present (append to list or keep first?)
        # Let's keep a list of sources
        if "source_metadata" in part:
            if "sources" not in merged:
                merged["sources"] = []
                if "source_metadata" in merged:
                    merged["sources"].append(merged["source_metadata"])
                    del merged["source_metadata"]
            
            merged["sources"].append(part["source_metadata"])

    merged["ingredients"] = list(all_ingredients)
    merged["steps"] = all_steps
    
    return merged

def stitch_recipes(data_dir: str, archive_dir: str, fix: bool = False):
    path = Path(data_dir)
    files = list(path.glob("*.json"))
    
    # Group by base name
    groups = defaultdict(list)
    
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                recipe = json.load(f)
                name = recipe.get("name", "")
                
                base, part = parse_part_info(name)
                if base and part:
                    groups[base].append((part, p, recipe))
        except Exception as e:
            print(f"Error reading {p}: {e}")

    # Filter for groups with > 1 part
    stitchable = {k: v for k, v in groups.items() if len(v) > 1}
    
    print(f"Found {len(stitchable)} multi-part recipe groups.")
    
    for base, parts in stitchable.items():
        # Sort by part number
        parts.sort(key=lambda x: x[0])
        
        print(f"Group: {base}")
        for part_num, p, _ in parts:
            print(f"  - Part {part_num}: {p.name}")
            
        if fix and archive_dir:
            archive_path = Path(archive_dir)
            archive_path.mkdir(parents=True, exist_ok=True)
            
            # Merge
            recipe_parts = [r for _, _, r in parts]
            merged_recipe = merge_recipes(recipe_parts)
            
            # Save merged
            # Use the filename of the first part but strip the part suffix if possible
            # Or just use a clean name
            safe_name = base.lower().replace(" ", "_") + "_stitched.json"
            dest_file = path / safe_name
            
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(merged_recipe, f, indent=2, ensure_ascii=False)
            
            print(f"  -> Merged to: {safe_name}")
            
            # Archive parts
            for _, p, _ in parts:
                shutil.move(str(p), str(archive_path / p.name))
                
            print("  -> Archived parts")
        print("-" * 20)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, required=True, help="Directory to scan")
    parser.add_argument("--archive", type=str, help="Directory to archive parts")
    parser.add_argument("--fix", action="store_true", help="Perform stitching")
    
    args = parser.parse_args()
    
    if args.fix and not args.archive:
        print("Error: --archive is required when using --fix")
    else:
        stitch_recipes(args.dir, args.archive, args.fix)
