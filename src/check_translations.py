import json
from pathlib import Path

def check_translations(data_dir: str = "data/parsed"):
    print(f"Checking translations in {data_dir}...")
    
    parsed_dir = Path(data_dir)
    merged_dir = parsed_dir / "merged"
    
    # Collect all recipe files
    all_files = list(parsed_dir.glob("*.json")) + list(merged_dir.glob("*.json"))
    
    # Map base names to available languages
    # Filename patterns:
    # - English (original): {base}_parsed.json
    # - English (translated): {base}_en_parsed.json
    # - Other: {base}_{lang}_parsed.json
    
    recipe_map = {}
    
    for file_path in all_files:
        if file_path.name.startswith("_"): continue
        
        name = file_path.name
        # Remove extension
        stem = file_path.stem # e.g. recipe_en_parsed_2
        
        # Remove counter if present (e.g. _2, _3)
        parts = stem.split("_")
        if parts[-1].isdigit():
            stem = "_".join(parts[:-1])
            
        # Now stem is likely recipe_en_parsed or recipe_it_parsed or recipe_parsed
        
        if stem.endswith("_merged"):
            base = stem.replace("_merged", "")
            lang = "en_merged"
        elif stem.endswith("_en_parsed"):
            base = stem.replace("_en_parsed", "")
            lang = "en_translated"
        elif stem.endswith("_parsed"):
            # Check for other languages
            is_other = False
            for l in ["it", "es", "fr", "de", "pt"]:
                if stem.endswith(f"_{l}_parsed"):
                    base = stem.replace(f"_{l}_parsed", "")
                    lang = l
                    is_other = True
                    break
            
            if not is_other:
                # Must be original English (or generic)
                base = stem.replace("_parsed", "")
                lang = "en_original"
        else:
            base = stem
            lang = "unknown"
                
        if base not in recipe_map:
            recipe_map[base] = set()
        recipe_map[base].add(lang)
        
    # Analyze coverage
    total_recipes = len(recipe_map)
    fully_covered = 0
    missing_english = []
    
    for base, langs in recipe_map.items():
        has_english = "en_original" in langs or "en_translated" in langs or "en_merged" in langs
        
        if has_english:
            fully_covered += 1
        else:
            missing_english.append(base)
            
    print("\n" + "="*50)
    print("TRANSLATION COVERAGE REPORT")
    print("="*50)
    print(f"Total Unique Recipes: {total_recipes}")
    print(f"Available in English: {fully_covered}")
    print(f"Missing English Version: {len(missing_english)}")
    print(f"Coverage: {fully_covered/total_recipes*100:.1f}%")
    print("="*50)
    
    if missing_english:
        print("\nRecipes missing English version (Sample):")
        for base in missing_english[:10]:
            print(f"  - {base}")

if __name__ == "__main__":
    check_translations()
