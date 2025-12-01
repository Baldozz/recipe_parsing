import json
from pathlib import Path
import statistics

def count_detailed_recipes(data_dir: str = "data/parsed"):
    print(f"Analyzing detailed recipes in {data_dir}...")
    
    parsed_dir = Path(data_dir)
    merged_dir = parsed_dir / "merged"
    
    valid_recipes = []
    
    # Collect all potential recipe files (excluding subdirectories like trash/incomplete)
    files = list(parsed_dir.glob("*.json")) + list(merged_dir.glob("*.json"))
    
    for file_path in files:
        if file_path.name.startswith("_"): continue
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            
            # Criteria for "full detailed": has both ingredients and steps
            if ingredients and steps:
                valid_recipes.append({
                    "name": data.get("name"),
                    "file": file_path.name,
                    "ingredient_count": len(ingredients),
                    "step_count": len(steps),
                    "language": data.get("other_details", {}).get("language", "unknown")
                })
                
        except Exception:
            pass
            
    # Stats
    total = len(valid_recipes)
    if total == 0:
        print("No detailed recipes found.")
        return

    avg_ingredients = statistics.mean(r["ingredient_count"] for r in valid_recipes)
    avg_steps = statistics.mean(r["step_count"] for r in valid_recipes)
    
    languages = {}
    for r in valid_recipes:
        lang = r["language"]
        languages[lang] = languages.get(lang, 0) + 1
        
    print("\n" + "="*50)
    print("DETAILED RECIPE ANALYSIS")
    print("="*50)
    print(f"Total Full Recipes: {total}")
    print(f"Average Ingredients: {avg_ingredients:.1f}")
    print(f"Average Steps: {avg_steps:.1f}")
    print("-" * 30)
    print("Language Breakdown:")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lang}: {count}")
    print("="*50)

if __name__ == "__main__":
    count_detailed_recipes()
