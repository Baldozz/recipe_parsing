import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Configuration
PARSED_DIR = Path("recipe_parsing/data/parsed")
CLASSIFIED_DIR = Path("recipe_parsing/data/classified")
API_KEY = os.environ.get("GEMINI_API_KEY")

# Fallback to the key found in config.py if not in env
if not API_KEY:
    API_KEY = "REDACTED" 

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in .env")

genai.configure(api_key=API_KEY)

CATEGORIES_PROMPT = """
Classify the recipe based on the following 8 categories. Choose the BEST fit.

1. Dish Type:
   - Amuse-bouche / Canapé
   - Starter / Appetizer
   - Main Course
   - Side Dish
   - Dessert
   - Petit Fours / Mignardise
   - Breakfast / Brunch
   - Drink
   - Component / Base (Stocks, Sauces, Pastes, Garnishes, Doughs)

2. Country / Cuisine of Origin:
   - French
   - Italian
   - Indian
   - Chinese
   - Japanese
   - Thai / SE Asian
   - Middle Eastern
   - Mediterranean
   - Latin American
   - British
   - American
   - Nordic
   - Other

3. Cooking Difficulty Level:
   - Level 1 (Easy / Rustic)
   - Level 2 (Intermediate / Professional)
   - Level 3 (Advanced / Michelin)

4. Main Ingredient:
   - Meat (Beef, Pork, Lamb, Game)
   - Poultry (Chicken, Duck)
   - Fish & Seafood
   - Vegetable-Forward
   - Starch/Grain (Pasta, Rice, Bread)
   - Fruit
   - Dairy / Egg
   - Other

5. Dietary & Allergens (Select all that apply, comma separated string):
   - Gluten-Free
   - Dairy-Free
   - Nut-Free
   - Vegetarian
   - Vegan
   - Pescatarian
   - Alcohol-Free
   - None

6. Occasion & Vibe:
   - Fine Dining / Plated
   - Family Style / Sharing
   - Buffet / Batch
   - Casual / Comfort
   - Healthy / Wellness
   - Kids Friendly

7. Preparation Style:
   - Quick / A la Minute
   - Make-Ahead / Prep-Heavy
   - Slow-Cooked / Braised
   - Baking / Pastry
   - Modernist / Molecular
   - Raw / Cured

8. Seasonality:
   - Spring
   - Summer
   - Autumn
   - Winter
   - Year-Round

OUTPUT FORMAT (JSON ONLY):
{
  "dish_type": "...",
  "cuisine": "...",
  "difficulty": "...",
  "main_ingredient": "...",
  "dietary": ["..."],
  "occasion": "...",
  "prep_style": "...",
  "seasonality": "..."
}
"""

def classify_recipe(file_path: Path) -> Optional[str]:
    try:
        relative_path = file_path.relative_to(PARSED_DIR)
        output_path = CLASSIFIED_DIR / relative_path
        
        if output_path.exists():
            return f"Skipped (Exists): {file_path.name}"

        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 'name' not in data:
            return f"Skipped (Invalid): {file_path.name}"

        model = genai.GenerativeModel('gemini-2.0-flash')
        
        recipe_text = f"""
        Name: {data.get('name', 'Unknown')}
        Ingredients: {json.dumps(data.get('ingredients', []), indent=2)}
        Steps: {json.dumps(data.get('steps', []), indent=2)}
        """
        
        prompt = f"""
        You are an expert private chef.
        {CATEGORIES_PROMPT}
        
        RECIPE TO CLASSIFY:
        {recipe_text}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        classification = json.loads(text)
        
        if classification:
            data['classifications'] = classification
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return f"Classified: {data.get('name')}"
            
    except Exception as e:
        return f"Error {file_path.name}: {str(e)}"
    
    return None

def main():
    print("Starting Parallel Recipe Classification...")
    CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)
    
    files = list(PARSED_DIR.rglob("*.json"))
    print(f"Found {len(files)} recipes to process.")
    
    # Use 10 threads for speed (Gemini Flash has high throughput)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(classify_recipe, f): f for f in files}
        
        for future in tqdm(as_completed(futures), total=len(files)):
            result = future.result()
            # if result and "Error" in result:
            #     print(result)

    print("Classification Complete.")

if __name__ == "__main__":
    main()
