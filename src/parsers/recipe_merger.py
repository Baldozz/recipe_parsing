"""
Recipe merger module for handling recipes split across multiple documents.

This module provides functionality to:
1. Detect recipe parts (e.g., "Part 1", "Part 2", "(continued)")
2. Identify incomplete recipes
3. Merge recipe parts into complete recipes
"""

import re
from typing import Dict, List
from pathlib import Path
import json


def detect_recipe_part(recipe_name: str) -> tuple[str, str | None]:
    """
    Detect if a recipe name indicates it's part of a multi-part recipe.
    
    Args:
        recipe_name: The recipe name to analyze
    
    Returns:
        Tuple of (base_name, part_indicator)
        - base_name: Recipe name without part indicators
        - part_indicator: The part indicator (e.g., "part_1", "continued") or None
    
    Examples:
        "Chocolate Cake - Part 1" -> ("Chocolate Cake", "part_1")
        "Pasta (Part 2)" -> ("Pasta", "part_2")
        "Soup (continued)" -> ("Soup", "continued")
        "Simple Recipe" -> ("Simple Recipe", None)
    """
    # Patterns to detect parts
    patterns = [
        (r'\s*[-–—]\s*part\s*(\d+)', 'part_{}'),  # "- Part 1"
        (r'\s*\(part\s*(\d+)\)', 'part_{}'),       # "(Part 1)"
        (r'\s*part\s*(\d+)', 'part_{}'),           # "Part 1"
        (r'\s*[-–—]\s*(\d+)(?:st|nd|rd|th)?\s*part', 'part_{}'),  # "- 1st part"
        (r'\s*\(continued\)', 'continued'),         # "(continued)"
        (r'\s*[-–—]\s*continued', 'continued'),     # "- continued"
        (r'\s*\(cont\.?\)', 'continued'),           # "(cont.)" or "(cont)"
    ]
    
    for pattern, part_format in patterns:
        match = re.search(pattern, recipe_name, re.IGNORECASE)
        if match:
            # Remove the part indicator from the name
            base_name = re.sub(pattern, '', recipe_name, flags=re.IGNORECASE).strip()
            
            # Format the part indicator
            if '{}' in part_format:
                part_indicator = part_format.format(match.group(1))
            else:
                part_indicator = part_format
            
            return base_name, part_indicator
    
    return recipe_name, None


def is_incomplete_recipe(recipe: dict) -> bool:
    """
    Check if a recipe appears to be incomplete.
    
    A recipe is considered incomplete if:
    - It has no ingredients
    - It has no steps
    - It has a part indicator in the name
    
    Args:
        recipe: Recipe dictionary
    
    Returns:
        True if recipe appears incomplete
    """
    ingredients = recipe.get("ingredients", [])
    steps = recipe.get("steps", [])
    name = recipe.get("name", "")
    
    # Check for part indicators
    _, part_indicator = detect_recipe_part(name)
    if part_indicator:
        return True
    
    # Check for missing data
    if not ingredients or not steps:
        return True
    
    return False


def merge_recipe_parts(recipe_parts: List[dict]) -> dict:
    """
    Merge multiple recipe parts into a single complete recipe.
    
    Args:
        recipe_parts: List of recipe dictionaries to merge (should be in order)
    
    Returns:
        Merged recipe dictionary
    """
    if not recipe_parts:
        raise ValueError("Cannot merge empty list of recipes")
    
    if len(recipe_parts) == 1:
        return recipe_parts[0]
    
    # Start with the first recipe as base
    merged = {
        "name": "",
        "ingredients": [],
        "steps": [],
        "other_details": {}
    }
    
    # Determine the base name (without part indicators)
    base_name, _ = detect_recipe_part(recipe_parts[0].get("name", ""))
    merged["name"] = base_name
    
    # Merge ingredients (deduplicate while preserving order)
    seen_ingredients = set()
    for recipe in recipe_parts:
        for ingredient in recipe.get("ingredients", []):
            # Normalize for comparison
            normalized = ingredient.lower().strip()
            if normalized and normalized not in seen_ingredients:
                seen_ingredients.add(normalized)
                merged["ingredients"].append(ingredient)
    
    # Merge steps (concatenate in order)
    for recipe in recipe_parts:
        merged["steps"].extend(recipe.get("steps", []))
    
    # Merge other_details (later parts override earlier parts)
    for recipe in recipe_parts:
        if recipe.get("other_details"):
            merged["other_details"].update(recipe["other_details"])
    
    # Add metadata about the merge
    merged["other_details"]["merged_from_parts"] = len(recipe_parts)
    merged["other_details"]["original_names"] = [r.get("name", "") for r in recipe_parts]
    
    return merged


def group_recipe_parts(recipes: List[tuple[str, dict]]) -> Dict[str, List[tuple[str, dict]]]:
    """
    Group recipes by their base name, identifying parts that should be merged.
    
    Args:
        recipes: List of (filename, recipe_dict) tuples
    
    Returns:
        Dictionary mapping base_name to list of (filename, recipe_dict) tuples
    """
    groups = {}
    
    for filename, recipe in recipes:
        recipe_name = recipe.get("name", "unknown")
        base_name, part_indicator = detect_recipe_part(recipe_name)
        
        # Use base name as the grouping key
        if base_name not in groups:
            groups[base_name] = []
        
        groups[base_name].append((filename, recipe, part_indicator))
    
    return groups


def should_merge_group(group: List[tuple[str, dict, str | None]]) -> bool:
    """
    Determine if a group of recipes should be merged.
    
    Args:
        group: List of (filename, recipe_dict, part_indicator) tuples
    
    Returns:
        True if the group should be merged
    """
    if len(group) <= 1:
        return False
    
    # Check if any recipe has a part indicator
    has_part_indicator = any(part for _, _, part in group)
    
    # Check if any recipe is incomplete
    has_incomplete = any(is_incomplete_recipe(recipe) for _, recipe, _ in group)
    
    return has_part_indicator or has_incomplete


def sort_recipe_parts(group: List[tuple[str, dict, str | None]]) -> List[dict]:
    """
    Sort recipe parts in the correct order for merging.
    
    Args:
        group: List of (filename, recipe_dict, part_indicator) tuples
    
    Returns:
        Sorted list of recipe dictionaries
    """
    def get_sort_key(item):
        filename, recipe, part_indicator = item
        
        if not part_indicator:
            return (0, filename)  # No part indicator, sort first
        
        if part_indicator == "continued":
            return (999, filename)  # "continued" goes last
        
        if part_indicator.startswith("part_"):
            try:
                part_num = int(part_indicator.split("_")[1])
                return (part_num, filename)
            except (IndexError, ValueError):
                return (500, filename)
        
        return (500, filename)  # Unknown format
    
    sorted_group = sorted(group, key=get_sort_key)
    return [recipe for _, recipe, _ in sorted_group]
