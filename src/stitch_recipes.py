import json
import os
import re
from pathlib import Path
from typing import List, Dict

def load_json(filepath: Path) -> Dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath: Path, data: Dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def stitch_recipes(parsed_dir: str):
    """
    Scans the parsed directory for recipes that are continuations of others.
    Merges them into the main recipe and archives the partial files.
    """
    parsed_path = Path(parsed_dir)
    json_files = sorted([f for f in parsed_path.iterdir() if f.suffix == ".json"])
    
    print(f"Scanning {len(json_files)} files for stitching...")
    
    # Map normalized names to their file paths and content
    # We use a list to handle duplicate names (though parser should avoid them)
    recipes_by_name = {}
    
    for file_path in json_files:
        try:
            content = load_json(file_path)
            # Handle list of recipes or single recipe object
            if isinstance(content, list):
                if len(content) == 1:
                    content = content[0]
                else:
                    continue
            
            name = content.get("name", "").strip()
            if not name:
                continue
                
            if name not in recipes_by_name:
                recipes_by_name[name] = []
            
            recipes_by_name[name].append({
                "file_path": file_path,
                "content": content
            })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Group files by their "Base Name"
    grouped_recipes = {}
    
    for name, entries in recipes_by_name.items():
        # Regex to find base name and suffix
        match = re.search(r"^(.*?)\s+\((?:[Cc]ontinued|[Pp]art\s+\d+|[Ff]inishing|[Aa]cabado|[Pp]resentation|[Pp]resentación)(?:\s+\d+)?\)$", name)
        
        if match:
            base_name = match.group(1).strip()
            suffix = name[len(base_name):].strip()
        else:
            base_name = name
            suffix = ""
            
        if base_name not in grouped_recipes:
            grouped_recipes[base_name] = []
        
        for entry in entries:
            grouped_recipes[base_name].append({
                "original_name": name,
                "suffix": suffix,
                "data": entry
            })
        
    # Process groups
    stitched_count = 0
    
    for base_name, parts in grouped_recipes.items():
        if len(parts) < 2:
            continue
            
        print(f"Found group for '{base_name}': {[p['original_name'] for p in parts]}")
        
        # Sort parts: Base (empty suffix) first, then Part 1, Part 2, etc.
        # We need a robust sort key.
        def sort_key(part):
            s = part["suffix"].lower()
            if not s: return 0 # Main recipe first
            if "part" in s:
                # Extract number
                nums = re.findall(r"\d+", s)
                if nums: return int(nums[0])
            if "continued" in s:
                nums = re.findall(r"\d+", s)
                return 100 + (int(nums[0]) if nums else 1)
            if "finishing" in s or "acabado" in s or "presentation" in s:
                return 999 # Last
            return 50 # Unknown suffix
            
        parts.sort(key=sort_key)
        
        # Merge into the first part (which becomes the main recipe)
        main_part = parts[0]
        main_recipe = main_part["data"]["content"]
        
        # Update name to Base Name (remove suffix if it was "Part 1")
        main_recipe["name"] = base_name
        
        # Initialize source_files
        source_files = []
        
        # Helper to add source
        def add_source(recipe_data):
            src_meta = recipe_data.get("source_metadata", {})
            filename = src_meta.get("filename", "unknown")
            if filename not in source_files:
                source_files.append(filename)

        add_source(main_recipe)
        
        for i in range(1, len(parts)):
            next_part = parts[i]
            next_recipe = next_part["data"]["content"]
            
            print(f"  Merging '{next_part['original_name']}' into '{base_name}'")
            
            add_source(next_recipe)
            
            # Append ingredients
            if "ingredients" in next_recipe:
                # Add a header to separate sections if not present
                first_ing = next_recipe["ingredients"][0] if next_recipe["ingredients"] else ""
                if not first_ing.startswith("##"):
                    header_name = next_part["suffix"] if next_part["suffix"] else f"Part {i+1}"
                    header = f"## {header_name}"
                    main_recipe.setdefault("ingredients", []).append(header)
                
                main_recipe.setdefault("ingredients", []).extend(next_recipe["ingredients"])
            
            # Append steps
            if "steps" in next_recipe:
                first_step = next_recipe["steps"][0] if next_recipe["steps"] else ""
                if not first_step.startswith("##"):
                    header_name = next_part["suffix"] if next_part["suffix"] else f"Part {i+1}"
                    header = f"## {header_name}"
                    main_recipe.setdefault("steps", []).append(header)
                    
                main_recipe.setdefault("steps", []).extend(next_recipe["steps"])
                
            # Merge other details
            if "other_details" in next_recipe:
                main_recipe.setdefault("other_details", {}).update(next_recipe["other_details"])
                
            # Archive the merged part
            archive_dir = parsed_path / "stitched_parts"
            archive_dir.mkdir(exist_ok=True)
            
            old_path = next_part["data"]["file_path"]
            new_path = archive_dir / old_path.name
            if old_path.exists(): 
                os.rename(old_path, new_path)
        
        # Save source_files
        main_recipe.setdefault("other_details", {})["source_files"] = source_files
        
        # Save the final merged recipe
        # If the main part was "Recipe (Part 1)", we rename the file to "Recipe.json"
        final_filename = f"{base_name.lower().replace(' ', '_')}_parsed.json"
        # Sanitize filename properly
        final_filename = re.sub(r'[^a-z0-9_]', '', final_filename.replace('_parsed.json', '')) + "_parsed.json"
        
        final_path = parsed_path / final_filename
        save_json(final_path, main_recipe)
        print(f"  Saved merged recipe to: {final_filename}")
        
        # If the main part file was different from final_path, archive it too
        if main_part["data"]["file_path"] != final_path:
             archive_dir = parsed_path / "stitched_parts"
             archive_dir.mkdir(exist_ok=True)
             old_path = main_part["data"]["file_path"]
             new_path = archive_dir / old_path.name
             if old_path.exists():
                os.rename(old_path, new_path)

        stitched_count += 1
                
    print(f"Stitching complete. Created {stitched_count} merged recipes.")

if __name__ == "__main__":
    stitch_recipes("data/parsed")
