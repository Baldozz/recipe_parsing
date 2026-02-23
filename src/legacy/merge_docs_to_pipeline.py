import shutil
from pathlib import Path

def merge_docs_to_pipeline():
    parsed_dir = Path("data/parsed")
    merged_dir = Path("data/merged_llm")
    merged_dir.mkdir(parents=True, exist_ok=True)
    
    # Sources
    sources = [parsed_dir / "docx", parsed_dir / "excel"]
    
    count = 0
    for source in sources:
        if not source.exists():
            continue
            
        print(f"Processing {source}...")
        for json_file in source.glob("*.json"):
            if "_parsed.json" in json_file.name:
                # Target name: foo_parsed.json -> foo_merged.json
                # This tricks classify_recipes.py into picking it up
                new_name = json_file.name.replace("_parsed.json", "_merged.json")
                target_path = merged_dir / new_name
                
                shutil.copy2(json_file, target_path)
                print(f"  Copied {json_file.name} -> {new_name}")
                count += 1
                
    print(f"\nMoved {count} document recipes to {merged_dir}")

if __name__ == "__main__":
    merge_docs_to_pipeline()
