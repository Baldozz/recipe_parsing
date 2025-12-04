import json
from pathlib import Path
from collections import Counter

MERGED_DIR = "data/merged_llm"

def analyze_quality():
    path = Path(MERGED_DIR)
    files = list(path.glob("*.json"))
    
    total_files = len(files)
    merged_count = 0
    has_ingredients = 0
    has_steps = 0
    types = Counter()
    
    print(f"Analyzing {total_files} recipes in {MERGED_DIR}...\n")
    
    for p in files:
        with open(p, 'r') as f:
            data = json.load(f)
            
        # Check for merges
        # A merged recipe usually has multiple source files OR we can check if it was a target
        # But our script appends 'source_files' list when merging.
        if len(data.get('source_files', [])) > 0:
            merged_count += 1
            
        # Completeness
        if data.get('ingredients') and len(data['ingredients']) > 0:
            has_ingredients += 1
        
        if data.get('steps') and len(data['steps']) > 0:
            has_steps += 1
            
        # Type
        r_type = data.get('recipe_type', 'unknown')
        types[r_type] += 1

    print("=== DATASET QUALITY REPORT ===")
    print(f"Total Recipes: {total_files}")
    print(f"Merged Recipes: {merged_count} ({(merged_count/total_files)*100:.1f}%)")
    print(f"Recipes with Ingredients: {has_ingredients} ({(has_ingredients/total_files)*100:.1f}%)")
    print(f"Recipes with Steps: {has_steps} ({(has_steps/total_files)*100:.1f}%)")
    print("\nRecipe Types:")
    for t, c in types.most_common():
        print(f"  - {t}: {c}")

if __name__ == "__main__":
    analyze_quality()
