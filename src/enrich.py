import json
import os
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from src.config import get_chat_client, CHAT_MODEL

SYSTEM_PROMPT = """You are an expert Executive Chef and Culinary Data Architect.
I will give you a recipe in JSON format.
Analyze the ingredients, techniques, plating style, and cultural origins.
Return a JSON object with ONLY the following extra metadata fields.

1. "cuisine_country": [
   - Identify the primary COUNTRY of origin.
   - CRITICAL RULE: Check `other_details` for `original_language`.
     - If `original_language` is 'es', prioritize "Spain".
     - If `original_language` is 'it', prioritize "Italy".
     - If `original_language` is 'fr', prioritize "France".
   - CRITICAL RULE: Pay close attention to the recipe NAME.
     - "Ali Oli" -> Spain
     - "Aioli" -> France (unless `original_language` is 'es')
     - "Tortilla" (potato) -> Spain
   - Use standard names (e.g., "Italy", "France", "India", "China", "USA", "UK").
   - Use "International" for generic dishes that are not strictly associated with one country (e.g., "Vegetable Soup", "Grilled Chicken").
   - Do NOT use regions (e.g., do not use "Tuscany", use "Italy").
   - If Fusion, list the top 2 countries (e.g., ["Japan", "Peru"]).
]

2. "kitchen_style": [
   - Select EXACTLY ONE:
   - "Fine Dining" (High technique, tweezed plating, expensive ingredients, sous-vide, foams)
   - "Bistro" (Elevated comfort food, brasserie style, hearty but refined)
   - "Home Cooking" (Rustic, family style, simple techniques, "grandma" style)
   - "Street Food" (Punchy flavors, handheld, fried, fast)
   - "Modern/Avant-Garde" (Molecular gastronomy, experimental)
   - "Bakery/Patisserie" (Breads, pastries, cakes)
]

3. "course_type": [Select ONE: "Amuse-bouche", "Starter", "Main", "Side", "Dessert", "Petit Fours", "Cocktail"]

4. "primary_protein": [e.g., Beef, Pork, Poultry, Game, Fish, Shellfish, Eggs, Dairy, Cheese, Tofu, Beans/Legumes, None]

5. "seasonality": [List all that apply based on ingredients: "Spring", "Summer", "Autumn", "Winter", "All-Year"]

6. "flavor_profile": [List top 2: e.g., "Umami", "Sweet", "Acidic", "Spicy", "Bitter", "Smoky", "Herbaceous"]

7. "texture_profile": [e.g., "Crispy", "Soft/Creamy", "Chewy", "Soupy", "Firm"]

8. "dietary_tags": [List valid flags: "Gluten-Free", "Dairy-Free", "Nut-Free", "Shellfish-Free", "Vegan", "Vegetarian"]

9. "wine_pairing_category": [Select ONE broad category: "Full-bodied Red", "Light Red", "Crisp White", "Rich White", "Sparkling", "Sweet/Fortified", "Sake/Rice Wine", "Beer", "None"]

10. "prep_complexity": ["Low", "Medium", "High"]

Output format: JSON object only. Do not include markdown formatting like ```json.
"""

def enrich_recipe(recipe: dict) -> Optional[dict]:
    """
    Enrich a single recipe with metadata using the LLM.
    Returns the enriched metadata dict, or None if failed.
    """
    client = get_chat_client()
    
    # Prepare the input for the LLM
    # We send the name, ingredients, and steps to keep context manageable but sufficient
    recipe_context = {
        "name": recipe.get("name", ""),
        "ingredients": recipe.get("ingredients", []),
        "steps": recipe.get("steps", []),
        "other_details": recipe.get("other_details", {})
    }
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(recipe_context)}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
            
        return json.loads(content)
        
    except Exception as e:
        print(f"Error enriching recipe {recipe.get('name')}: {e}")
        return None

def enrich_all(source_dir: str, dest_dir: str, limit: int = 0):
    """
    Enrich all recipes in source_dir and save to dest_dir.
    Skips files that already exist in dest_dir.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    files = list(source_path.glob("*.json"))
    if limit > 0:
        files = files[:limit]
        
    print(f"Found {len(files)} recipes in {source_dir}")
    
    for file_path in tqdm(files, desc="Enriching recipes"):
        dest_file = dest_path / file_path.name
        
        if dest_file.exists():
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                recipe = json.load(f)
                
            metadata = enrich_recipe(recipe)
            
            if metadata:
                # Merge metadata into the recipe
                # We'll add it at the top level as requested/planned
                recipe.update(metadata)
                
                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(recipe, f, ensure_ascii=False, indent=2)
            else:
                print(f"Skipping {file_path.name} - failed to generate metadata")
                
        except Exception as e:
            print(f"Failed to process {file_path.name}: {e}")

if __name__ == "__main__":
    # For testing
    pass
