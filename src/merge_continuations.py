"""
Merge recipe continuations based on is_continuation_of flag.

Replaces complex prompt-based naming with simple post-processing.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def get_timestamp_from_filename(filename):
    """Extract timestamp from filename like '20190828_185128.jpg'."""
    try:
        # Assumes format YYYYMMDD_HHMMSS at start of filename
        timestamp_str = filename.split('.')[0]
        # Handle potential suffixes like _2, _3 if they exist before extension
        if '_' in timestamp_str and len(timestamp_str.split('_')) > 2:
             # e.g. 20190828_185128_2 -> 20190828_185128
             parts = timestamp_str.split('_')
             timestamp_str = f"{parts[0]}_{parts[1]}"
             
        return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except (ValueError, IndexError):
        return None

import unicodedata

def normalize_string(s):
    """Normalize string to ASCII, lower case, removing accents."""
    if not s:
        return ""
    # Normalize unicode characters (e.g. ü -> u)
    nfkd_form = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()

def merge_continuations(parsed_dir: str, output_dir: str):
    """
    Merge recipes marked with is_continuation_of flag.
    
    Args:
        parsed_dir: Directory with parsed recipes
        output_dir: Where to save merged recipes
    """
    parsed_path = Path(parsed_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load all recipes in order (recursive to find english/original folders)
    all_files = sorted(parsed_path.rglob("*_parsed.json"))
    recipes = []
    
    for file_path in all_files:
        with open(file_path, 'r') as f:
            recipe = json.load(f)
            recipe['_source_file'] = file_path.stem
            
            # Extract timestamp
            filename = recipe.get('source_metadata', {}).get('filename', '')
            recipe['_timestamp'] = get_timestamp_from_filename(filename)
            
            recipes.append(recipe)
    
    print(f"Loaded {len(recipes)} recipes")
    
    # Sort by timestamp to ensure correct session grouping
    # Handle None timestamps by putting them at the end
    recipes.sort(key=lambda x: (x.get('_timestamp') or datetime.max, x.get('source_metadata', {}).get('filename', ''), x.get('name')))
    
    # Assign Session IDs
    current_session_id = 0
    last_timestamp = object() # Sentinel
    last_source_file = None
    
    for recipe in recipes:
        timestamp = recipe.get('_timestamp')
        source_file = recipe.get('source_metadata', {}).get('filename')
        
        if timestamp is None:
            # No timestamp -> Group by source file
            if source_file != last_source_file:
                current_session_id += 1
            
            recipe['_session_id'] = current_session_id
            last_source_file = source_file
            last_timestamp = object() # Reset timestamp tracking
        else:
            # Check time delta
            is_new_session = True
            if isinstance(last_timestamp, datetime):
                delta = (timestamp - last_timestamp).total_seconds()
                if delta <= 60: # 60 second threshold
                    is_new_session = False
            
            if is_new_session:
                current_session_id += 1
            
            recipe['_session_id'] = current_session_id
            last_timestamp = timestamp
            last_source_file = None # Reset source file tracking
            
    print("Assigned session IDs based on 60s threshold.")
    
    # Group continuations
    merged_recipes = []
    # Group by Session
    sessions = defaultdict(list)
    for recipe in recipes:
        sessions[recipe['_session_id']].append(recipe)
        
    print(f"Grouped into {len(sessions)} sessions.")
    
    merged_recipes = []
    recipe_map = {}  # name -> accumulated recipe
    redirect_map = {} # merged_name -> target_name (for chains)
    continuation_count = 0
    
    # Process each session
    for session_id, session_recipes in sorted(sessions.items()):
        # SAFETY VALVE: If session is too huge, it's likely a grouping error.
        # Skip auto-merge for this session to prevent "black hole" merging.
        if len(session_recipes) > 50:
            print(f"WARNING: Session {session_id} has {len(session_recipes)} recipes. Skipping auto-merge for safety.")
            for r in session_recipes:
                # Treat as standalone
                if r['name'] not in recipe_map:
                    recipe_map[r['name']] = r.copy()
                    recipe_map[r['name']]['source_files'] = [r.get('source_metadata', {}).get('filename', 'unknown')]
                    recipe_map[r['name']]['source_images'] = [r.get('source_metadata', {}).get('link', '')]
                    merged_recipes.append(recipe_map[r['name']])
            continue

        # 1. Identify Anchor for this session
        anchor = None
        # Priority 1: Explicit 'main' recipe
        mains = [r for r in session_recipes if r.get('recipe_type') == 'main']
        if mains:
            anchor = mains[0] # Use the first main
        
        # Priority 2: 'assembly' recipe (if no main)
        if not anchor:
            assemblies = [r for r in session_recipes if r.get('recipe_type') == 'assembly']
            if assemblies:
                anchor = assemblies[0]
                
        # Priority 3: First recipe (fallback)
        if not anchor and session_recipes:
             anchor = session_recipes[0]
             
        if not anchor:
            continue
            
        print(f"Session {session_id}: Anchor is '{anchor['name']}' (Type: {anchor.get('recipe_type')})")
            
        # Register Anchor first
        if anchor['name'] not in recipe_map:
            recipe_map[anchor['name']] = anchor.copy()
            recipe_map[anchor['name']]['source_files'] = [anchor.get('source_metadata', {}).get('filename', 'unknown')]
            recipe_map[anchor['name']]['source_images'] = [anchor.get('source_metadata', {}).get('link', '')]
            merged_recipes.append(recipe_map[anchor['name']])
        
        # 2. Merge others into Anchor
        for recipe in session_recipes:
            if recipe['name'] == anchor['name']:
                continue # Skip the anchor itself
                
            # Check explicit continuation
            continuation_of = recipe.get('is_continuation_of')
            target_name = None
            
            print(f"  Processing '{recipe['name']}' (Type: {recipe.get('recipe_type')}) - Continuation: {continuation_of}")
            
            if continuation_of:
                # Try to resolve explicit link
                if continuation_of in recipe_map:
                    target_name = continuation_of
                elif continuation_of in redirect_map:
                    target_name = redirect_map[continuation_of]
                else:
                    # Try normalized
                    norm = normalize_string(continuation_of)
                    for k in recipe_map:
                        if normalize_string(k) == norm:
                            target_name = k
                            break
            
            # If no explicit link (or link failed), use Anchor (Same Session Rule)
            if not target_name:
                if anchor:
                    # REFINEMENT: Only auto-merge orphans if:
                    # 1. The anchor is an "Assembly" (generic bucket)
                    # 2. OR the names are similar (e.g. "Prawn Dredge" -> "Prawn")
                    # 3. OR the orphan is explicitly a "preparation" type (usually safe to merge)
                    
                    anchor_name = anchor['name']
                    orphan_name = recipe['name']
                    
                    is_assembly_anchor = anchor.get('recipe_type') == 'assembly'
                    is_prep_orphan = recipe.get('recipe_type') == 'preparation'
                    is_assembly_orphan = recipe.get('recipe_type') == 'assembly'
                    
                    # Check if session has multiple mains
                    num_mains = len([r for r in session_recipes if r.get('recipe_type') == 'main'])
                    has_multiple_mains = num_mains > 1
                    
                    # Simple name similarity: check if any significant word matches
                    # STOP WORDS to ignore (common culinary terms that don't imply identity)
                    STOP_WORDS = {'soup', 'sauce', 'salad', 'cake', 'rice', 'pork', 'beef', 
                                  'fish', 'meat', 'dish', 'with', 'and', 'the', 'for',
                                  'fried', 'baked', 'roast', 'grilled', 'steam', 'boil',
                                  'filling', 'stock', 'dressing', 'paste', 'dough', 'oil'}
                    # Removed 'duck' from stop words to allow Tea Duck linking
                    
                    anchor_words = set(w.lower() for w in anchor_name.split() if w.lower() not in STOP_WORDS and len(w) > 2)
                    orphan_words = set(w.lower() for w in orphan_name.split() if w.lower() not in STOP_WORDS and len(w) > 2)
                    
                    common_words = anchor_words.intersection(orphan_words)
                    
                    # Stricter rule for Main -> Main merge
                    if recipe.get('recipe_type') == 'main' and anchor.get('recipe_type') == 'main':
                        # Require at least 2 common words for Main-to-Main (e.g. "Bloody Wong Tong" vs "Wong Tong")
                        has_name_overlap = len(common_words) >= 2
                    else:
                        # For components/preps, 1 common word is enough (e.g. "Prawn Dredge" -> "Prawn")
                        has_name_overlap = len(common_words) >= 1
                    
                    # DECISION LOGIC
                    should_merge = False
                    
                    if has_name_overlap:
                        should_merge = True
                    elif is_assembly_anchor:
                        should_merge = True
                    elif (is_prep_orphan or is_assembly_orphan) and not has_multiple_mains:
                        # Only auto-merge generic parts if there is ONLY ONE Main in the session.
                        # If multiple mains exist, we can't be sure which one it belongs to without name overlap.
                        should_merge = True
                    
                    if should_merge:
                        print(f"  -> Auto-linking orphaned '{orphan_name}' to '{anchor_name}' (Session {session_id})")
                        target_name = anchor_name
                    else:
                        print(f"  -> Skipping auto-link for '{orphan_name}' to '{anchor_name}' (No name overlap/type match)")
                else:
                    print(f"  -> No anchor for session {session_id}, keeping '{recipe['name']}' separate.")
                    # It's a distinct recipe (e.g. another Main in same session?), treat as new
                    pass

            if target_name:
                # MERGE
                base_recipe = recipe_map[target_name]
                
                # Deduplication Check
                is_duplicate = False
                if (recipe.get('ingredients') == base_recipe.get('ingredients') and 
                    recipe.get('steps') == base_recipe.get('steps')):
                    is_duplicate = True
                    print(f"  -> Detected DUPLICATE content for '{recipe['name']}'. Merging metadata only.")
                    duplicates_list.append({
                        "kept_file": base_recipe.get('source_metadata', {}).get('filename'),
                        "duplicate_file": recipe.get('source_metadata', {}).get('filename'),
                        "recipe_name": recipe['name']
                    })

                print(f"Merging '{recipe['name']}' into '{target_name}'")
                
                if not is_duplicate:
                    # Merge ingredients
                    if recipe.get('ingredients'):
                        if base_recipe.get('ingredients'):
                            base_recipe['ingredients'].append(f"## {recipe.get('name', 'Continued')}")
                        base_recipe.setdefault('ingredients', []).extend(recipe['ingredients'])
                    
                    # Merge steps
                    if recipe.get('steps'):
                        if base_recipe.get('steps'):
                            base_recipe['steps'].append(f"## {recipe.get('name', 'Continued')}")
                        base_recipe.setdefault('steps', []).extend(recipe['steps'])
                
                # Merge metadata
                base_recipe.setdefault('source_files', []).append(recipe.get('source_metadata', {}).get('filename', 'unknown'))
                base_recipe.setdefault('source_images', []).append(recipe.get('source_metadata', {}).get('link', ''))
                
                for key, value in recipe.get('other_details', {}).items():
                    if key not in base_recipe.get('other_details', {}):
                        base_recipe.setdefault('other_details', {})[key] = value
                        
                redirect_map[recipe['name']] = target_name
                continuation_count += 1
            
            else:
                # Treat as new standalone recipe
                if recipe['name'] not in recipe_map:
                    recipe_map[recipe['name']] = recipe.copy()
                    recipe_map[recipe['name']]['source_files'] = [recipe.get('source_metadata', {}).get('filename', 'unknown')]
                    recipe_map[recipe['name']]['source_images'] = [recipe.get('source_metadata', {}).get('link', '')]
                    merged_recipes.append(recipe_map[recipe['name']])
        
        # SECOND PASS: Orphan Clustering
        # Try to merge remaining orphans in this session with EACH OTHER
        # e.g. "Tea Duck Brine" + "To Finish Duck" (neither merged into Goose)
        
        # Get all recipes currently in recipe_map that belong to this session AND were just added
        # (We can filter merged_recipes by session_id if we tracked it, but we popped it.
        #  Instead, let's look at the names we just processed)
        
        session_recipe_names = [r['name'] for r in session_recipes]
        orphans = [r for r in merged_recipes if r['name'] in session_recipe_names and r['name'] != anchor['name']]
        
        # Simple N^2 clustering
        for i, r1 in enumerate(orphans):
            for r2 in orphans[i+1:]:
                # Check overlap
                name1 = r1['name']
                name2 = r2['name']
                
                words1 = set(w.lower() for w in name1.split() if w.lower() not in STOP_WORDS and len(w) > 2)
                words2 = set(w.lower() for w in name2.split() if w.lower() not in STOP_WORDS and len(w) > 2)
                
                common = words1.intersection(words2)
                if common:
                    print(f"  -> Clustering Orphan '{name1}' into '{name2}' (Common: {common})")
                    
                    # Merge r1 into r2
                    # (We need to update r2 in merged_recipes and REMOVE r1)
                    
                    # Merge Logic (Same as above)
                    if r1.get('ingredients'):
                        if r2.get('ingredients'):
                            r2['ingredients'].append(f"## {r1.get('name', 'Continued')}")
                        r2.setdefault('ingredients', []).extend(r1['ingredients'])
                    
                    if r1.get('steps'):
                        if r2.get('steps'):
                            r2['steps'].append(f"## {r1.get('name', 'Continued')}")
                        r2.setdefault('steps', []).extend(r1['steps'])
                        
                    r2.setdefault('source_files', []).extend(r1.get('source_files', []))
                    r2.setdefault('source_images', []).extend(r1.get('source_images', []))
                    
                    # Mark r1 for removal
                    r1['_to_remove'] = True
                    break # Moved r1, stop checking r1
        
        # Remove merged orphans
        merged_recipes = [r for r in merged_recipes if not r.get('_to_remove')]
    
    # Save merged recipes
    duplicates_list = []
    
    for recipe in merged_recipes:
        # Clean up internal fields
        recipe.pop('_source_file', None)
        recipe.pop('is_continuation_of', None)
        recipe.pop('_session_id', None)
        recipe.pop('_timestamp', None)
        
        # Generate filename from recipe name
        safe_name = recipe['name'].lower()
        safe_name = safe_name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
        safe_name = safe_name[:100]  # Limit length
        
        output_file = output_path / f"{safe_name}_merged.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, indent=2, ensure_ascii=False)
            
    # Save duplicates report
    if duplicates_list:
        report_path = output_path.parent / "duplicates_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(duplicates_list, f, indent=2, ensure_ascii=False)
        print(f"  -> Saved {len(duplicates_list)} duplicates to {report_path}")

    print(f"\n{'='*80}")
    print(f"Merging complete:")
    print(f"  Input: {len(recipes)} recipes")
    print(f"  Merged: {continuation_count} continuations")
    print(f"  Output: {len(merged_recipes)} final recipes")
    print(f"{'='*80}\n")
    
    return merged_recipes


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 merge_continuations.py <parsed_dir> <output_dir>")
        sys.exit(1)
    
    parsed_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    merge_continuations(parsed_dir, output_dir)
