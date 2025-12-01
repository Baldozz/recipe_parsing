"""
Recipe deduplication module for detecting and removing duplicate recipes.

This module provides functionality to:
1. Calculate recipe similarity
2. Detect duplicate recipes
3. Choose the best version when duplicates are found
"""

import json
from typing import List, Tuple, Optional
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace and lowercasing."""
    return " ".join(text.lower().split())


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    normalized1 = normalize_text(text1)
    normalized2 = normalize_text(text2)
    return SequenceMatcher(None, normalized1, normalized2).ratio()


def calculate_recipe_similarity(recipe1: dict, recipe2: dict) -> float:
    """
    Calculate overall similarity between two recipes.
    
    Compares:
    - Recipe names (weight: 0.5)
    - Ingredients (weight: 0.3)
    - Steps (weight: 0.2)
    
    Args:
        recipe1: First recipe dictionary
        recipe2: Second recipe dictionary
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Compare names
    name1 = recipe1.get("name", "")
    name2 = recipe2.get("name", "")
    name_similarity = calculate_similarity(name1, name2)
    
    # Boost similarity if one name contains the other (and they are not too short)
    if len(name1) > 5 and len(name2) > 5:
        if name1.lower() in name2.lower() or name2.lower() in name1.lower():
            name_similarity = max(name_similarity, 0.9)

    # Compare ingredients
    ingredients1 = " ".join(recipe1.get("ingredients", []))
    ingredients2 = " ".join(recipe2.get("ingredients", []))
    ingredients_similarity = calculate_similarity(ingredients1, ingredients2)
    
    # Compare steps
    steps1 = " ".join(recipe1.get("steps", []))
    steps2 = " ".join(recipe2.get("steps", []))
    steps_similarity = calculate_similarity(steps1, steps2)
    
    # Weighted average
    overall_similarity = (
        name_similarity * 0.5 +
        ingredients_similarity * 0.3 +
        steps_similarity * 0.2
    )
    
    return overall_similarity


def is_duplicate(recipe1: dict, recipe2: dict, threshold: float = 0.80) -> bool:
    """
    Determine if two recipes are duplicates.
    
    Args:
        recipe1: First recipe dictionary
        recipe2: Second recipe dictionary
        threshold: Similarity threshold (default: 0.80)
    
    Returns:
        True if recipes are considered duplicates
    """
    similarity = calculate_recipe_similarity(recipe1, recipe2)
    return similarity >= threshold


def choose_best_recipe(recipes: List[dict]) -> dict:
    """
    Choose the best version from a list of duplicate recipes.
    
    Criteria (in order of priority):
    1. Most complete (has all fields filled)
    2. Most ingredients
    3. Most steps
    4. Longest other_details
    
    Args:
        recipes: List of duplicate recipe dictionaries
    
    Returns:
        The best recipe from the list
    """
    if not recipes:
        raise ValueError("Cannot choose from empty list")
    
    if len(recipes) == 1:
        return recipes[0]
    
    def score_recipe(recipe: dict) -> tuple:
        """Score a recipe for comparison."""
        ingredients_count = len(recipe.get("ingredients", []))
        steps_count = len(recipe.get("steps", []))
        other_details_len = len(json.dumps(recipe.get("other_details", {})))
        
        # Check completeness
        has_name = bool(recipe.get("name", "").strip())
        has_ingredients = ingredients_count > 0
        has_steps = steps_count > 0
        completeness = sum([has_name, has_ingredients, has_steps])
        
        # Return tuple for sorting (higher is better)
        return (completeness, ingredients_count, steps_count, other_details_len)
    
    # Sort by score (descending) and return the best
    sorted_recipes = sorted(recipes, key=score_recipe, reverse=True)
    return sorted_recipes[0]


def find_duplicates(recipes: List[Tuple[str, dict]], threshold: float = 0.80) -> dict:
    """
    Find duplicate recipes in a list.
    
    Args:
        recipes: List of (filename, recipe_dict) tuples
        threshold: Similarity threshold for duplicates
    
    Returns:
        Dictionary mapping representative recipe to list of duplicates:
        {
            "recipe_name": {
                "best": (filename, recipe_dict),
                "duplicates": [(filename, recipe_dict), ...]
            }
        }
    """
    if not recipes:
        return {}
    
    duplicate_groups = {}
    processed = set()
    
    for i, (filename1, recipe1) in enumerate(recipes):
        if i in processed:
            continue
        
        # Start a new group with this recipe
        group = [(filename1, recipe1)]
        
        # Find all duplicates of this recipe
        for j, (filename2, recipe2) in enumerate(recipes):
            if i == j or j in processed:
                continue
            
            if is_duplicate(recipe1, recipe2, threshold):
                group.append((filename2, recipe2))
                processed.add(j)
        
        processed.add(i)
        
        # Only store groups with duplicates
        if len(group) > 1:
            # Choose the best recipe from the group
            best_recipe = choose_best_recipe([r for _, r in group])
            best_filename = next(f for f, r in group if r == best_recipe)
            
            recipe_name = recipe1.get("name", f"recipe_{i}")
            duplicate_groups[recipe_name] = {
                "best": (best_filename, best_recipe),
                "duplicates": [item for item in group if item[0] != best_filename]
            }
    
    return duplicate_groups


def deduplicate_recipes(recipes: List[Tuple[str, dict]], threshold: float = 0.80) -> Tuple[List[Tuple[str, dict]], dict]:
    """
    Remove duplicate recipes from a list, keeping only the best version.
    
    Args:
        recipes: List of (filename, recipe_dict) tuples
        threshold: Similarity threshold for duplicates
    
    Returns:
        Tuple of (deduplicated_recipes, duplicate_report)
        - deduplicated_recipes: List of unique recipes
        - duplicate_report: Information about removed duplicates
    """
    duplicate_groups = find_duplicates(recipes, threshold)
    
    if not duplicate_groups:
        return recipes, {}
    
    # Create set of filenames to remove
    filenames_to_remove = set()
    for group_info in duplicate_groups.values():
        for filename, _ in group_info["duplicates"]:
            filenames_to_remove.add(filename)
    
    # Filter out duplicates
    deduplicated = [(f, r) for f, r in recipes if f not in filenames_to_remove]
    
    # Create report
    report = {
        "total_recipes": len(recipes),
        "unique_recipes": len(deduplicated),
        "duplicates_removed": len(recipes) - len(deduplicated),
        "duplicate_groups": duplicate_groups
    }
    
    return deduplicated, report
