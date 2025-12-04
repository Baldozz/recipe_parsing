"""
Scan parsed recipes and identify problematic ones for review/re-parsing.

Categories:
1. Empty recipes (no ingredients AND no steps)
2. Ingredient-only (has ingredients but no steps)
3. Step-only (has steps but no ingredients)
4. Suspiciously short (< 2 ingredients OR < 2 steps)
"""

import json
from pathlib import Path
from collections import defaultdict


def scan_parsed_recipes(parsed_dir="data/parsed"):
    """Scan all parsed recipes and categorize issues."""
    
    parsed_path = Path(parsed_dir)
    all_files = sorted(parsed_path.glob("*_parsed.json"))
    
    issues = defaultdict(list)
    stats = {
        'total': 0,
        'healthy': 0,
        'empty': 0,
        'no_steps': 0,
        'no_ingredients': 0,
        'suspicious': 0
    }
    
    for file_path in all_files:
        try:
            with open(file_path, 'r') as f:
                recipe = json.load(f)
            
            stats['total'] += 1
            
            name = recipe.get('name', 'Unknown')
            ingredients = recipe.get('ingredients', [])
            steps = recipe.get('steps', [])
            source = recipe.get('source_metadata', {}).get('filename', 'unknown')
            
            has_ingredients = len(ingredients) > 0
            has_steps = len(steps) > 0
            
            issue_found = False
            
            # Check for empty recipe
            if not has_ingredients and not has_steps:
                issues['empty'].append({
                    'name': name,
                    'file': file_path.name,
                    'source': source,
                    'reason': 'No ingredients AND no steps'
                })
                stats['empty'] += 1
                issue_found = True
            
            # Check for ingredient-only (likely component lists or parsing error)
            elif has_ingredients and not has_steps:
                issues['no_steps'].append({
                    'name': name,
                    'file': file_path.name,
                    'source': source,
                    'ingredients_count': len(ingredients),
                    'reason': 'Has ingredients but no steps'
                })
                stats['no_steps'] += 1
                issue_found = True
            
            # Check for step-only (unusual but possible for assembly)
            elif has_steps and not has_ingredients:
                # This is actually OK for "assembly" type recipes
                if recipe.get('recipe_type') != 'assembly':
                    issues['no_ingredients'].append({
                        'name': name,
                        'file': file_path.name,
                        'source': source,
                        'steps_count': len(steps),
                        'type': recipe.get('recipe_type', 'N/A'),
                        'reason': 'Has steps but no ingredients (not assembly)'
                    })
                    stats['no_ingredients'] += 1
                    issue_found = True
            
            # Check for suspiciously short recipes
            elif (len(ingredients) < 2 and len(steps) < 2) and recipe.get('recipe_type') == 'main':
                issues['suspicious'].append({
                    'name': name,
                    'file': file_path.name,
                    'source': source,
                    'ingredients_count': len(ingredients),
                    'steps_count': len(steps),
                    'reason': 'Very short for a main dish'
                })
                stats['suspicious'] += 1
                issue_found = True
            
            if not issue_found:
                stats['healthy'] += 1
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return issues, stats


def print_report(issues, stats):
    """Print a formatted report of issues."""
    
    print("\n" + "="*80)
    print("RECIPE PARSING ISSUES REPORT")
    print("="*80)
    
    print(f"\nOVERALL STATISTICS:")
    print(f"  Total recipes: {stats['total']}")
    print(f"  Healthy: {stats['healthy']} ({stats['healthy']/stats['total']*100:.1f}%)")
    print(f"  With issues: {stats['total'] - stats['healthy']} ({(stats['total']-stats['healthy'])/stats['total']*100:.1f}%)")
    
    print(f"\nISSUE BREAKDOWN:")
    print(f"  Empty recipes: {stats['empty']}")
    print(f"  No steps (ingredients only): {stats['no_steps']}")
    print(f"  No ingredients: {stats['no_ingredients']}")
    print(f"  Suspiciously short: {stats['suspicious']}")
    
    # Detail each category
    for category, items in issues.items():
        if items:
            print(f"\n{'='*80}")
            print(f"{category.upper().replace('_', ' ')} ({len(items)} recipes)")
            print(f"{'='*80}")
            
            for item in items[:20]:  # Show first 20
                print(f"\n  Recipe: {item['name']}")
                print(f"  File: {item['file']}")
                print(f"  Source: {item['source']}")
                print(f"  Reason: {item['reason']}")
                if 'ingredients_count' in item:
                    print(f"  Ingredients: {item['ingredients_count']}")
                if 'steps_count' in item:
                    print(f"  Steps: {item['steps_count']}")
            
            if len(items) > 20:
                print(f"\n  ... and {len(items) - 20} more")
    
    # Save detailed report to JSON
    output_file = Path("data/problematic_recipes_report.json")
    with open(output_file, 'w') as f:
        json.dump({
            'stats': stats,
            'issues': issues
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Detailed report saved to: {output_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    issues, stats = scan_parsed_recipes()
    print_report(issues, stats)
