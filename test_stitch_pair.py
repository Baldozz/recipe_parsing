import json
import os
import sys
from pathlib import Path

# Add src to path so internal imports work
sys.path.append('src')

from src.stitch_sessions_llm import analyze_image_pair
import google.generativeai as genai

# Setup
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

def test_pair():
    print("Testing Multimodal Merge on IMG_1495 -> IMG_1496...")
    
    # Paths
    base_dir = Path("/Users/fabiobaldini/Desktop/Projects/Ludo_Project/RAG_RECIPES/recipe_parsing")
    img1_path = base_dir / "data/raw/jpg_recipes/IMG_1495.JPG"
    img2_path = base_dir / "data/raw/jpg_recipes/IMG_1496.JPG"
    
    json1_path = base_dir / "data/parsed/english/creamy_sweetbreads_parsed.json"
    json2_path = base_dir / "data/parsed/english/finishing_and_presentation_parsed.json"
    
    # Load Data
    with open(json1_path, 'r') as f:
        r1 = json.load(f)
    with open(json2_path, 'r') as f:
        r2 = json.load(f)
        
    # Prepare Input Structure
    # Note: The main script expects a list of recipes for each image
    data1 = {
        "filename": "IMG_1495.JPG",
        "recipes": [{"name": r1['name'], "type": r1.get('recipe_type'), "ingredients": r1.get('ingredients', [])[:5]}]
    }
    data2 = {
        "filename": "IMG_1496.JPG",
        "recipes": [{"name": r2['name'], "type": r2.get('recipe_type'), "ingredients": r2.get('ingredients', [])[:5]}]
    }
    
    # Run Analysis
    print(f"Image 1: {img1_path}")
    print(f"Image 2: {img2_path}")
    
    result = analyze_image_pair(str(img1_path), data1, str(img2_path), data2)
    
    print("\nLLM Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_pair()
