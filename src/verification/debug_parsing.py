import os
import json
from pathlib import Path
from src.parsers.multimodal_parser import parse_recipe_group
from src.config import CHAT_MODEL
import google.generativeai as genai

# Setup
RAW_DIR = Path("data/raw/jpg_recipes")
GROUP_FILES = [
    "IMG_4740.jpeg",
    "IMG_4741.jpeg",
    "IMG_4742.jpeg",
    "IMG_4743.jpeg",
    "IMG_4744.jpeg",
    "IMG_4745.jpeg",
    "IMG_4746.jpeg",
    "IMG_4747.jpeg",
    "IMG_4748.jpeg",
    "IMG_4749.jpeg"
]

def debug_group():
    print(f"--- DEBUGGING GROUP: {GROUP_FILES[0]} ---")
    
    # 1. Verify files exist
    paths = []
    for f in GROUP_FILES:
        p = RAW_DIR / f
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            return
        paths.append(str(p))
        
    print(f"Found {len(paths)} images.")
    
    # 2. Run Parsing with the CURRENT configuration
    # We want to see the RAW output if possible, but the function returns parsed JSON.
    # To debug, we might need to modify the parser temporarily or just trust the result.
    # Let's run it and see what "No recipes found" actually looks like (failed JSON or empty list?)
    
    print(f"Model: {CHAT_MODEL}")
    
    try:
        model = genai.GenerativeModel(CHAT_MODEL)
        recipes = parse_recipe_group(paths, model=model)
        
        print("\n--- RESULT ---")
        print(json.dumps(recipes, indent=2))
        
        if not recipes:
            print("\n❌ RESULT IS EMPTY LIST (No recipes found)")
        else:
            print(f"\n✅ Found {len(recipes)} recipes")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")

if __name__ == "__main__":
    debug_group()
