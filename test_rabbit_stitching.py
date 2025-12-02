import json
from pathlib import Path
from src.stitch_recipes import merge_recipes, parse_part_info

def main():
    files = [
        "data/parsed/rabbit_and_pork_dumplings_in_jade_soup_parsed.json",
        "data/parsed/rabbit_and_pork_dumplings_in_jade_soup_continued_parsed.json",
        "data/parsed/rabbit_and_pork_dumplings_in_jade_soup_continued_parsed_2.json",
        "data/parsed/rabbit_and_pork_dumplings_in_jade_soup_continued_parsed_3.json",
        "data/parsed/rabbit_and_pork_dumplings_in_jade_soup_continued_parsed_4.json"
    ]

    parts = []
    print("Loading files...")
    for f_path in files:
        with open(f_path, "r") as f:
            recipe = json.load(f)
            # We need to simulate the sorting logic
            # The main file usually doesn't have "Part 1" in the name, so we treat it as part 1 if others are continuations
            # But let's see what parse_part_info says
            name = recipe.get("name", "")
            base, part = parse_part_info(name)
            
            # Manual override for this test if regex doesn't catch "Continued" implies Part 2, etc.
            # The filenames give a hint.
            if "continued_parsed_4" in f_path: part = 5
            elif "continued_parsed_3" in f_path: part = 4
            elif "continued_parsed_2" in f_path: part = 3
            elif "continued_parsed" in f_path: part = 2
            else: part = 1
            
            print(f"Loaded Part {part}: {name}")
            parts.append(recipe)

    # Sort by the part number we assigned
    # (In the real script, it groups by base name and sorts by detected part number)
    # Here we just rely on the order I put them in the list which corresponds to 1, 2, 3, 4, 5
    # But let's be safe
    # Actually, merge_recipes expects a list of dicts. It assumes they are sorted.
    
    print("\n--- Merging Rabbit Dumplings Recipe ---")
    merged = merge_recipes(parts)
    
    print(json.dumps(merged, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
