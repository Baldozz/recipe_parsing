"""
Verify known complex multi-page recipes are correctly stitched.

Tests specific recipes we know should be merged:
1. Rabbit and Pork Dumpling in Jade Soup
2. Colomba (multiple parts)
3. CANTUCCI AND VIN SANTO
4. Bloody Wong Tong
"""

import json
from pathlib import Path
from collections import defaultdict


KNOWN_MULTI_PAGE_RECIPES = {
    "Rabbit and Pork Dumpling": {
        "expected_files": ["20190828_185128.jpg", "20190828_185200.jpg", "20190828_185219.jpg"],
        "keywords": ["rabbit", "jade", "dumpling"]
    },
    "Colomba": {
        "expected_files": [],  # Multiple files, need to discover
        "keywords": ["colomb", "rinfresco", "impasto"]
    },
    "CANTUCCI": {
        "expected_files": ["20210427_235004.jpg", "20210427_235008.jpg"],
        "keywords": ["cantucci", "vin santo"]
    },
    "Bloody Wong Tong": {
        "expected_files": [],  # Check for beetroot/wong related files
        "keywords": ["wong", "beetroot", "fermented"]
    }
}


def find_related_recipes(parsed_dir, keywords):
    """Find all recipes matching keywords."""
    parsed_path = Path(parsed_dir)
    matches = []
    
    for file_path in sorted(parsed_path.glob("*_parsed.json")):
        try:
            with open(file_path, 'r') as f:
                recipe = json.load(f)
            
            name_lower = recipe.get('name', '').lower()
            
            # Check if any keyword matches
            if any(kw in name_lower for kw in keywords):
                matches.append({
                    'name': recipe.get('name'),
                    'file': file_path.name,
                    'source': recipe.get('source_metadata', {}).get('filename', 'unknown'),
                    'type': recipe.get('recipe_type', 'N/A'),
                    'ingredients_count': len(recipe.get('ingredients', [])),
                    'steps_count': len(recipe.get('steps', [])),
                    'is_continuation_of': recipe.get('is_continuation_of'),
                    'related_to': recipe.get('related_to')
                })
        except Exception as e:
            pass
    
    return matches


def check_stitched_recipes(stitched_dir, recipe_base_name, keywords):
    """Check if recipe parts were stitched in Phase 2."""
    stitched_path = Path(stitched_dir)
    
    if not stitched_path.exists():
        return None, "Stitched directory doesn't exist yet (Phase 2 not run)"
    
    matches = []
    for file_path in sorted(stitched_path.glob("*.json")):
        try:
            with open(file_path, 'r') as f:
                recipe = json.load(f)
            
            name_lower = recipe.get('name', '').lower()
            if any(kw in name_lower for kw in keywords):
                source_files = recipe.get('source_files', [])
                matches.append({
                    'name': recipe.get('name'),
                    'file': file_path.name,
                    'source_files': source_files,
                    'parts_count': len(source_files) if isinstance(source_files, list) else 1,
                    'type': recipe.get('recipe_type', 'N/A')
                })
        except Exception as e:
            pass
    
    return matches, None


def verify_known_recipes(parsed_dir="data/parsed", stitched_dir="data/stitched"):
    """Verify all known multi-page recipes."""
    
    print("\n" + "="*80)
    print("KNOWN MULTI-PAGE RECIPES VERIFICATION")
    print("="*80)
    
    for recipe_name, config in KNOWN_MULTI_PAGE_RECIPES.items():
        print(f"\n{'='*80}")
        print(f"CHECKING: {recipe_name}")
        print(f"{'='*80}")
        
        # Phase 1: Check parsed recipes
        parsed_matches = find_related_recipes(parsed_dir, config['keywords'])
        print(f"\nPhase 1 (Parsed): Found {len(parsed_matches)} related recipes")
        
        if parsed_matches:
            # Group by base name (without _2, _3 suffixes)
            name_groups = defaultdict(list)
            for match in parsed_matches:
                # Remove _2, _3 etc from name for grouping
                base = match['name'].split('(')[0].strip()
                name_groups[base].append(match)
            
            for base_name, parts in name_groups.items():
                if len(parts) > 1:
                    print(f"\n  ⚠️  Multiple parts detected for '{base_name}':")
                    for part in parts:
                        print(f"    - {part['name']} (from {part['source']})")
                        print(f"      Type: {part['type']}, {part['ingredients_count']} ingredients, {part['steps_count']} steps")
                        if part['is_continuation_of']:
                            print(f"      -> Continues: {part['is_continuation_of']}")
                        if part['related_to']:
                            print(f"      -> Related to: {part['related_to']}")
                else:
                    print(f"\n  ✓ Single recipe: {parts[0]['name']}")
        
        # Phase 2: Check stitched recipes
        stitched_matches, error = check_stitched_recipes(stitched_dir, recipe_name, config['keywords'])
        
        if error:
            print(f"\nPhase 2 (Stitched): {error}")
        elif stitched_matches:
            print(f"\nPhase 2 (Stitched): Found {len(stitched_matches)} stitched recipes")
            for match in stitched_matches:
                print(f"\n  ✓ {match['name']}")
                print(f"    File: {match['file']}")
                print(f"    Parts: {match['parts_count']}")
                if match['source_files']:
                    print(f"    Sources: {', '.join(match['source_files'][:3])}{'...' if len(match['source_files']) > 3 else ''}")
    
    print(f"\n{'='*80}")
    print("VERIFICATION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    verify_known_recipes()
