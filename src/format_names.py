import json
from pathlib import Path

def title_case_names(dir_path: str):
    count = 0
    for path in Path(dir_path).rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if it's the expected dictionary format
            if isinstance(data, dict) and "name" in data:
                original_name = data["name"]
                
                # Title case the name
                # E.g. "SEA URCHIN AND COFFEE" -> "Sea Urchin And Coffee"
                new_name = original_name.title()
                
                if new_name != original_name:
                    data["name"] = new_name
                    
                    # Write it back
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    count += 1
                    
        except Exception as e:
            print(f"Skipping {path} - Error: {e}")
            
    print(f"Successfully converted {count} recipe names to Title Case in {dir_path}!")

if __name__ == "__main__":
    target_dir = "data/final_classified_english"
    print(f"Formatting recipe names in {target_dir}...")
    title_case_names(target_dir)
