import json
import shutil
import os
from pathlib import Path

def extract_english_recipes(data_dir: str = "data/parsed", output_dir: str = "data/english_recipes"):
    print(f"Extracting English recipes from {data_dir} to {output_dir}...")
    
    parsed_dir = Path(data_dir)
    merged_dir = parsed_dir / "merged"
    dest_dir = Path(output_dir)
    
    # Create output directory
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True)
    
    # Collect all potential recipe files
    # We only want files directly in data/parsed (excluding subdirs like incomplete/trash) 
    # and files in data/parsed/merged
    
    files_to_process = []
    
    # 1. Files in data/parsed (excluding directories)
    for f in parsed_dir.iterdir():
        if f.is_file() and f.suffix == ".json" and not f.name.startswith("_"):
            files_to_process.append(f)
            
    # 2. Files in data/parsed/merged
    if merged_dir.exists():
        for f in merged_dir.iterdir():
            if f.is_file() and f.suffix == ".json" and not f.name.startswith("_"):
                files_to_process.append(f)
    
    count = 0
    
    for file_path in files_to_process:
        stem = file_path.stem
        
        # Remove counter if present (e.g. _2, _3)
        parts = stem.split("_")
        if parts[-1].isdigit():
            stem = "_".join(parts[:-1])
            
        is_english = False
        
        # Logic to determine if English
        if stem.endswith("_merged"):
            is_english = True
        elif stem.endswith("_en_parsed"):
            is_english = True
        elif stem.endswith("_parsed"):
            # Check for other language codes
            is_other = False
            for l in ["it", "es", "fr", "de", "pt"]:
                if stem.endswith(f"_{l}_parsed"):
                    is_other = True
                    break
            
            if not is_other:
                is_english = True
        
        if is_english:
            shutil.copy2(file_path, dest_dir / file_path.name)
            count += 1
            
    print("\n" + "="*50)
    print("EXTRACTION COMPLETE")
    print("="*50)
    print(f"Total English Recipes Extracted: {count}")
    print(f"Destination: {dest_dir}")
    print("="*50)

if __name__ == "__main__":
    extract_english_recipes()
