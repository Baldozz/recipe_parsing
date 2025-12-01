import json
from pathlib import Path
import statistics

def analyze_english_dataset(data_dir: str = "data/english_recipes"):
    print(f"Analyzing English recipes in {data_dir}...")
    
    data_path = Path(data_dir)
    files = list(data_path.glob("*.json"))
    
    stats = {
        "total": 0,
        "original_english": 0,
        "translated": 0,
        "merged": 0,
        "ingredient_counts": [],
        "step_counts": []
    }
    
    for file_path in files:
        stats["total"] += 1
        name = file_path.stem
        
        # Determine type
        if "_merged" in name:
            stats["merged"] += 1
        elif "_en_parsed" in name:
            stats["translated"] += 1
        else:
            stats["original_english"] += 1
            
        # Content analysis
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats["ingredient_counts"].append(len(data.get("ingredients", [])))
                stats["step_counts"].append(len(data.get("steps", [])))
        except Exception:
            pass

    if stats["total"] == 0:
        print("No recipes found.")
        return

    avg_ing = statistics.mean(stats["ingredient_counts"]) if stats["ingredient_counts"] else 0
    avg_steps = statistics.mean(stats["step_counts"]) if stats["step_counts"] else 0

    print("\n" + "="*50)
    print("ENGLISH DATASET STATISTICS")
    print("="*50)
    print(f"Total Recipes: {stats['total']}")
    print("-" * 30)
    print("Source Breakdown:")
    print(f"  Original English: {stats['original_english']} ({(stats['original_english']/stats['total'])*100:.1f}%)")
    print(f"  Translated:       {stats['translated']} ({(stats['translated']/stats['total'])*100:.1f}%)")
    print(f"  Merged:           {stats['merged']} ({(stats['merged']/stats['total'])*100:.1f}%)")
    print("-" * 30)
    print("Content Quality:")
    print(f"  Avg Ingredients:  {avg_ing:.1f}")
    print(f"  Avg Steps:        {avg_steps:.1f}")
    print("="*50)

if __name__ == "__main__":
    analyze_english_dataset()
