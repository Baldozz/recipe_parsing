import json
from pathlib import Path
from collections import Counter
from tqdm import tqdm

def calculate_stats(data_dir: str):
    path = Path(data_dir)
    files = list(path.glob("*.json"))
    
    country_counter = Counter()
    total_recipes = 0
    
    print(f"Analyzing {len(files)} recipes...")
    
    for p in tqdm(files):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            countries = data.get("cuisine_country", [])
            if not countries:
                country_counter["Unknown"] += 1
            else:
                for c in countries:
                    country_counter[c] += 1
            
            total_recipes += 1
            
        except Exception as e:
            print(f"Error reading {p.name}: {e}")

    print("\n--- Cuisine Origin Statistics ---")
    print(f"Total Recipes Analyzed: {total_recipes}")
    print("\nTop Countries:")
    for country, count in country_counter.most_common():
        percentage = (count / total_recipes) * 100
        print(f"{country}: {count} ({percentage:.1f}%)")

if __name__ == "__main__":
    calculate_stats("data/enriched_recipes")
