import hashlib
import os
from pathlib import Path
from collections import defaultdict

def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_and_delete_duplicates(directory):
    hashes = defaultdict(list)
    image_extensions = {'.jpg', '.jpeg', '.png'}
    
    path = Path(directory)
    files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]
    
    print(f"Scanning {len(files)} files in {directory}...")
    
    for f in files:
        file_hash = calculate_md5(f)
        hashes[file_hash].append(f)
        
    duplicates_count = 0
    deleted_count = 0
    
    for file_hash, file_list in hashes.items():
        if len(file_list) > 1:
            duplicates_count += 1
            # Sort by filename length (shortest first), then alphabetically
            # This prefers "Image.jpg" over "Image copy.jpg"
            file_list.sort(key=lambda x: (len(x.name), x.name))
            
            keep = file_list[0]
            remove = file_list[1:]
            
            print(f"\nDuplicate Set ({file_hash}):")
            print(f"  Keeping: {keep.name}")
            for f in remove:
                print(f"  Deleting: {f.name}")
                try:
                    os.remove(f)
                    deleted_count += 1
                except OSError as e:
                    print(f"  Error deleting {f.name}: {e}")

    print(f"\nSummary:")
    print(f"Found {duplicates_count} sets of duplicates.")
    print(f"Deleted {deleted_count} files.")

if __name__ == "__main__":
    find_and_delete_duplicates("data/raw/jpg_recipes")
