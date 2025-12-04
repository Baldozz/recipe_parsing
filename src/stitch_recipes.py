"""
Enhanced Recipe Stitching: Merge continuations and build component relationships.

Phase 2 of the three-phase architecture:
1. Merge multi-part recipes (Part 2, Part 3)
2. Merge assembly sections into main recipes
3. Preserve recipe_type metadata
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def stitch_recipes(parsed_dir: str, output_dir: str):
    """
    Stitch multi-part recipes from parsed JSON files.
    
    Args:
        parsed_dir: Directory containing *_parsed.json files
        output_dir: Where to save stitched recipes
    """
    parsed_path = Path(parsed_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load all recipes
    all_files = sorted(parsed_path.glob("*_parsed.json"))
    print(f"Scanning {len(all_files)} files for stitching...\n")
    
    recipes_by_file = {}
    for file_path in all_files:
        with open(file_path, 'r') as f:
            recipe = json.load(f)
            recipes_by_file[file_path.stem] = recipe
    
    # Phase 2.1: Merge Continuations
    stitched_recipes, continuation_groups = merge_continuations(recipes_by_file)
    
    # Phase 2.2: Merge Assembly Sections
    final_recipes = merge_assembly_sections(stitched_recipes)
    
    # Save results
    merged_count = 0
    for filename, recipe in final_recipes.items():
        output_file = output_path / f"{filename}.json"
        with open(output_file, 'w') as f:
            json.dump(recipe, f, indent=2)
        
        # Check if this was a merged recipe
        if filename in continuation_groups:
            merged_count += 1
    
    print(f"\nStitching complete.")
    print(f"Created {len(final_recipes)} recipes ({merged_count} from merged continuations).")
    return final_recipes


def merge_continuations(recipes_by_file: dict) -> tuple[dict, dict]:
    """
    Merge multi-part recipes (e.g., Part 2, Part 3).
    
    Returns:
        (stitched_recipes, continuation_groups)
    """
    # Group recipes by base name
    recipe_groups = defaultdict(list)
    continuation_pattern = re.compile(r'^(.+?)\s*\((?:Part|Continued)\s*(\d+)?\)$', re.IGNORECASE)
    
    for filename, recipe in recipes_by_file.items():
        name = recipe.get('name', '')
        match = continuation_pattern.match(name)
        
        if match:
            # This is a continuation
            base_name = match.group(1).strip()
            recipe_groups[base_name].append((filename, recipe, name))
        else:
            # Could be the base recipe
            recipe_groups[name].append((filename, recipe, name))
    
    # Merge groups
    stitched_recipes = {}
    continuation_groups = {}
    
    for base_name, group in recipe_groups.items():
        if len(group) == 1:
            # No continuations, keep as-is
            filename, recipe, _ = group[0]
            stitched_recipes[filename] = recipe
        else:
            # Has continuations - merge them
            print(f"Found group for '{base_name}': {[name for _, _, name in group]}")
            
            # Sort by name to get base first, then Part 2, Part 3, etc.
            group = sorted(group, key=lambda x: x[2])
            
            # Start with the base recipe
            base_filename, base_recipe, _ = group[0]
            merged = base_recipe.copy()
            source_files = [base_recipe.get('source_metadata', {}).get('filename', 'unknown')]
            
            # Merge continuations
            for _, cont_recipe, cont_name in group[1:]:
                print(f"  Merging '{cont_name}' into '{base_name}'")
                
                # Add continuation header
                part_match = re.search(r'\((?:Part|Continued)\s*(\d+)?\)', cont_name, re.IGNORECASE)
                if part_match:
                    header = f"## ({part_match.group(0)[1:-1]})"  # Extract "Part 2" from "(Part 2)"
                else:
                    header = f"## (Continued)"
                
                # Merge ingredients
                if cont_recipe.get('ingredients'):
                    merged.setdefault('ingredients', []).append(header)
                    merged['ingredients'].extend(cont_recipe['ingredients'])
                
                # Merge steps
                if cont_recipe.get('steps'):
                    merged.setdefault('steps', []).append(header)
                    merged['steps'].extend(cont_recipe['steps'])
                
                # Track source file
                cont_source = cont_recipe.get('source_metadata', {}).get('filename', 'unknown')
                source_files.append(cont_source)
            
            # Update merged recipe
            merged['name'] = base_name
            merged['source_files'] = source_files
            
            # Save with base filename
            safe_name = base_name.lower().replace(' ', '_').replace('/', '_')
            stitched_recipes[safe_name + '_parsed'] = merged
            continuation_groups[safe_name + '_parsed'] = group
            
            print(f"  Saved merged recipe to: {safe_name}_parsed.json\n")
    
    return stitched_recipes, continuation_groups


def merge_assembly_sections(recipes: dict) -> dict:
    """
    Merge recipes with recipe_type="assembly" into their main recipes.
    
    Logic:
    - First, filter out empty recipes (no ingredients AND no steps)
    - If there's only one main recipe + one assembly → merge
    - If there are multiple mains, try to match by context (later enhancement)
    """
    # Filter out completely empty recipes
    filtered_recipes = {}
    for filename, recipe in recipes.items():
        has_ingredients = len(recipe.get('ingredients', [])) > 0
        has_steps = len(recipe.get('steps', [])) > 0
        
        if has_ingredients or has_steps:
            filtered_recipes[filename] = recipe
        else:
            print(f"Filtering out empty recipe: {recipe.get('name')}")
    
    # Separate by type
    assembly_recipes = []
    main_recipes = []
    other_recipes = {}
    
    for filename, recipe in filtered_recipes.items():
        recipe_type = recipe.get('recipe_type', 'main')
        
        if recipe_type == 'assembly':
            assembly_recipes.append((filename, recipe))
        elif recipe_type == 'main':
            main_recipes.append((filename, recipe))
        else:
            # Keep preparations and components as-is
            other_recipes[filename] = recipe
    
    # Simple case: If there's exactly 1 main and 1 assembly, merge them
    if len(main_recipes) == 1 and len(assembly_recipes) == 1:
        main_filename, main_recipe = main_recipes[0]
        assembly_filename, assembly_recipe = assembly_recipes[0]
        
        print(f"Merging assembly '{assembly_recipe.get('name')}' into '{main_recipe.get('name')}'")
        
        # Add assembly steps
        if assembly_recipe.get('steps'):
            main_recipe.setdefault('steps', []).append("## To Serve")
            main_recipe['steps'].extend(assembly_recipe['steps'])
        
        # Add assembly ingredients if any
        if assembly_recipe.get('ingredients'):
            main_recipe.setdefault('ingredients', []).append("## To Serve")
            main_recipe['ingredients'].extend(assembly_recipe['ingredients'])
        
        other_recipes[main_filename] = main_recipe
    else:
        # Keep all as-is for now (can enhance later with smart matching)
        for filename, recipe in main_recipes + assembly_recipes:
            other_recipes[filename] = recipe
    
    return other_recipes


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 stitch_recipes.py <parsed_dir> <output_dir>")
        sys.exit(1)
    
    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    stitch_recipes(parsed_dir, output_dir)
