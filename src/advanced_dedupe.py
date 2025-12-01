import json
import os
from pathlib import Path
from difflib import SequenceMatcher

def normalize_text(text):
    """Normalize text for comparison (lowercase, remove punctuation/spaces)"""
    return "".join(c.lower() for c in text if c.isalnum())

def get_similarity(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def advanced_deduplication(data_dir: str = "data/english_recipes"):
    print(f"Running advanced deduplication in {data_dir}...")
    
    data_path = Path(data_dir)
    files = sorted(list(data_path.glob("*.json")))
    
    # Group by base name (ignoring counters)
    # e.g. recipe_parsed.json and recipe_parsed_2.json
    groups = {}
    
    for f in files:
        stem = f.stem
        # Remove counter
        parts = stem.split("_")
        if parts[-1].isdigit():
            base = "_".join(parts[:-1])
        else:
            base = stem
            
        if base not in groups:
            groups[base] = []
        groups[base].append(f)
        
    deleted_count = 0
    
    for base, group_files in groups.items():
        if len(group_files) < 2:
            continue
            
        print(f"Checking group: {base} ({len(group_files)} files)")
        
        # Load content for all files in group
        contents = []
        for f in group_files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    # Create a signature based on ingredients
                    ingredients = " ".join(sorted(data.get("ingredients", [])))
                    steps = " ".join(data.get("steps", []))
                    contents.append({
                        "file": f,
                        "data": data,
                        "ing_sig": normalize_text(ingredients),
                        "step_sig": normalize_text(steps),
                        "step_count": len(data.get("steps", [])),
                        "ing_count": len(data.get("ingredients", []))
                    })
            except:
                pass
                
        # Compare every pair
        # We want to keep the "best" one. 
        # Heuristic for "best": Most steps (more granular) > Most ingredients > Shortest filename (usually original)
        
        # Sort by quality (descending)
        contents.sort(key=lambda x: (x["step_count"], x["ing_count"], -len(str(x["file"]))), reverse=True)
        
        kept = contents[0]
        to_remove = []
        
        for i in range(1, len(contents)):
            candidate = contents[i]
            
            # Check similarity
            ing_sim = get_similarity(kept["ing_sig"], candidate["ing_sig"])
            
            # If ingredients are very similar (>90%), check steps
            if ing_sim > 0.9:
                # If ingredients match, we assume it's the same recipe.
                # Since we sorted by quality, 'kept' is already better or equal.
                print(f"  Duplicate found: {candidate['file'].name}")
                print(f"    Match with: {kept['file'].name} (Ing Sim: {ing_sim:.2f})")
                to_remove.append(candidate["file"])
            
        # Execute deletion
        for f in to_remove:
            print(f"    DELETING: {f.name}")
            f.unlink()
            deleted_count += 1

    print("\n" + "="*50)
    print("ADVANCED DEDUPLICATION COMPLETE")
    print("="*50)
    print(f"Total Duplicates Deleted: {deleted_count}")
    print("="*50)

if __name__ == "__main__":
    advanced_deduplication()
