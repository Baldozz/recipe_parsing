import json
from pathlib import Path

MERGED_DIR = "data/merged_llm"

def audit_merges():
    path = Path(MERGED_DIR)
    files = list(path.glob("*.json"))
    
    merged_recipes = []
    potential_orphans = []
    
    suspicious_keywords = ["part", "finishing", "acabado", "serve", "assembly", "continuation"]
    
    print(f"Auditing {len(files)} files in {MERGED_DIR}...\n")
    
    for p in files:
        with open(p, 'r') as f:
            data = json.load(f)
            
        name = data.get('name', 'Unknown')
        source_files = data.get('source_files', [])
        
        # 1. Success: Has merged files
        if source_files:
            merged_recipes.append({
                "name": name,
                "merged_count": len(source_files),
                "sources": source_files
            })
            
        # 2. Potential Failure: No merged files BUT name looks like a fragment
        else:
            name_lower = name.lower()
            if any(k in name_lower for k in suspicious_keywords):
                # Exclude if it's a valid "Part 1" that is just the start
                # But usually "Part 2" is the orphan.
                potential_orphans.append(name)
                
    print("=== SUCCESSFUL MERGES (Recipes with stitched parts) ===")
    for m in merged_recipes:
        print(f"[x] {m['name']} (Merged {m['merged_count']} parts: {m['sources']})")
        
    print("\n=== POTENTIAL MISSES (Standalone files that look like fragments) ===")
    if not potential_orphans:
        print("None found! (Great sign)")
    else:
        for o in sorted(potential_orphans):
            print(f"[?] {o}")

if __name__ == "__main__":
    audit_merges()
