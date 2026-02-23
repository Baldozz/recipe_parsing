import json
from pathlib import Path
from collections import Counter

def analyze_summary(file_path, label):
    path = Path(file_path)
    if not path.exists():
        print(f"--- {label} ---")
        print("Summary file not found (Processing might be starting or failed).")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total = len(data)
        statuses = Counter(item.get('status', 'unknown') for item in data)
        
        print(f"--- {label} ---")
        print(f"Total Entries: {total}")
        for status, count in statuses.items():
            print(f"  {status.upper()}: {count}")
            
        if statuses.get('error'):
            print("\n  Error Breakdown:")
            errors = [item.get('message', 'No message') for item in data if item.get('status') == 'error']
            # Simple clustering of 429s vs others
            rate_limits = sum(1 for e in errors if "429" in e or "Quota exceeded" in e)
            others = len(errors) - rate_limits
            print(f"    Rate Limit (429): {rate_limits}")
            print(f"    Other Errors: {others}")

        success_recipes = sum(1 for item in data if item.get('status') == 'success')
        print(f"\n  Total Successful Recipes extracted: {success_recipes}")

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    base_dir = Path("data/parsed")
    analyze_summary(base_dir / "images/_processing_summary_images.json", "IMAGES")
    print("\n")
    analyze_summary(base_dir / "docx/_processing_summary_docx.json", "DOCX")
