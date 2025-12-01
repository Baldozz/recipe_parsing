import re
import shutil
from pathlib import Path
from collections import defaultdict
import argparse

def parse_version(filename):
    """
    Extract base name and version from filename.
    Examples:
    - recipe_parsed.json -> (recipe, 1)
    - recipe_parsed_2.json -> (recipe, 2)
    - recipe_parsed_10.json -> (recipe, 10)
    """
    # Regex to match: base_name + optional _parsed + optional _N + .json
    # We want to capture the base name and the version number
    
    # Common pattern seems to be: name_parsed(_N)?.json
    # But sometimes just name.json? Let's assume standard format from previous steps.
    
    match = re.search(r"^(.*?)_parsed(_(\d+))?\.json$", filename)
    if match:
        base = match.group(1)
        version_str = match.group(3)
        version = int(version_str) if version_str else 1
        return base, version
    
    # Fallback if _parsed is missing or different format
    return filename, 1

def find_duplicates(data_dir, archive_dir=None, fix=False):
    path = Path(data_dir)
    files = list(path.glob("*.json"))
    
    groups = defaultdict(list)
    
    for p in files:
        base, version = parse_version(p.name)
        groups[base].append((version, p))
        
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    
    print(f"Scanned {len(files)} files.")
    print(f"Found {len(duplicates)} groups with duplicates.\n")
    
    total_archived = 0
    
    for base, versions in duplicates.items():
        # Sort by version descending (highest first)
        versions.sort(key=lambda x: x[0], reverse=True)
        
        keep = versions[0]
        to_archive = versions[1:]
        
        print(f"Group: {base}")
        print(f"  Keep: {keep[1].name} (v{keep[0]})")
        for v, p in to_archive:
            print(f"  Archive: {p.name} (v{v})")
            
        if fix and archive_dir:
            archive_path = Path(archive_dir)
            archive_path.mkdir(parents=True, exist_ok=True)
            
            for v, p in to_archive:
                dest = archive_path / p.name
                shutil.move(str(p), str(dest))
                total_archived += 1
        print("-" * 20)

    if fix:
        print(f"\nTotal files archived: {total_archived}")
    elif duplicates:
        print("\nRun with --fix to archive older versions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, required=True, help="Directory to scan")
    parser.add_argument("--archive", type=str, help="Directory to move duplicates to")
    parser.add_argument("--fix", action="store_true", help="Move duplicates to archive")
    
    args = parser.parse_args()
    
    if args.fix and not args.archive:
        print("Error: --archive is required when using --fix")
    else:
        find_duplicates(args.dir, args.archive, args.fix)
