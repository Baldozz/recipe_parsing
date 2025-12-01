"""
Merge recipe parts that are split across multiple documents.

This module scans the parsed recipes directory, identifies recipe parts,
and merges them into complete recipes.
"""

from pathlib import Path
import json
from typing import List, Tuple

from src.parsers.recipe_merger import (
    group_recipe_parts,
    should_merge_group,
    sort_recipe_parts,
    merge_recipe_parts,
)
from src.ingest import sanitize_filename, get_unique_filename


def load_all_recipes(parsed_dir: str) -> List[Tuple[str, dict]]:
    """
    Load all parsed recipe JSON files from a directory.
    
    Args:
        parsed_dir: Directory containing parsed recipe JSON files
    
    Returns:
        List of (filename, recipe_dict) tuples
    """
    parsed_path = Path(parsed_dir)
    recipes = []
    
    for json_file in parsed_path.glob("*_parsed.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                recipe = json.load(f)
                recipes.append((json_file.name, recipe))
        except Exception as e:
            print(f"Warning: Could not load {json_file.name}: {e}")
    
    return recipes


def merge_recipes(parsed_dir: str) -> None:
    """
    Scan parsed recipes directory and merge recipe parts.
    
    Args:
        parsed_dir: Directory containing parsed recipe JSON files
    """
    print("=" * 60)
    print("Recipe Merger - Detecting and merging recipe parts")
    print("=" * 60)
    print()
    
    # Load all recipes
    print(f"Loading recipes from: {parsed_dir}")
    recipes = load_all_recipes(parsed_dir)
    print(f"Found {len(recipes)} recipe files\n")
    
    if not recipes:
        print("No recipes found to merge.")
        return
    
    # Group recipes by base name
    print("Grouping recipes by name...")
    groups = group_recipe_parts(recipes)
    print(f"Found {len(groups)} unique recipe names\n")
    
    # Identify groups that should be merged
    merge_candidates = []
    for base_name, group in groups.items():
        if should_merge_group(group):
            merge_candidates.append((base_name, group))
    
    if not merge_candidates:
        print("No recipe parts detected that need merging.")
        print("All recipes appear to be complete and standalone.")
        return
    
    print(f"Found {len(merge_candidates)} recipe(s) with multiple parts:\n")
    
    # Process each merge candidate
    merged_dir = Path(parsed_dir) / "merged"
    merged_dir.mkdir(exist_ok=True)
    
    merge_report = []
    
    for base_name, group in merge_candidates:
        print(f"Recipe: {base_name}")
        print(f"  Parts found: {len(group)}")
        
        # Sort parts in correct order
        sorted_recipes = sort_recipe_parts(group)
        
        # Show part details
        for i, (filename, recipe, part_indicator) in enumerate(group, 1):
            part_label = part_indicator if part_indicator else "main"
            print(f"    {i}. {filename} ({part_label})")
        
        # Merge the parts
        try:
            merged_recipe = merge_recipe_parts(sorted_recipes)
            
            # Save merged recipe
            sanitized_name = sanitize_filename(base_name)
            output_filename = get_unique_filename(str(merged_dir), f"{sanitized_name}_merged")
            output_path = merged_dir / output_filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(merged_recipe, indent=2, fp=f, ensure_ascii=False)
            
            print(f"  ✓ Merged into: {output_filename}")
            print(f"    - {len(merged_recipe.get('ingredients', []))} ingredients")
            print(f"    - {len(merged_recipe.get('steps', []))} steps")
            print()
            
            merge_report.append({
                "base_name": base_name,
                "parts_merged": len(group),
                "source_files": [filename for filename, _, _ in group],
                "output_file": output_filename,
                "status": "success"
            })
            
        except Exception as e:
            print(f"  ✗ Error merging: {e}\n")
            merge_report.append({
                "base_name": base_name,
                "parts_merged": len(group),
                "source_files": [filename for filename, _, _ in group],
                "status": "error",
                "error": str(e)
            })
    
    # Save merge report
    report_path = merged_dir / "_merge_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(merge_report, indent=2, fp=f, ensure_ascii=False)
    
    successful = sum(1 for r in merge_report if r["status"] == "success")
    print("=" * 60)
    print(f"Merge complete: {successful}/{len(merge_candidates)} successful")
    print(f"Merged recipes saved to: {merged_dir}")
    print(f"Merge report: {report_path}")
    print("=" * 60)
