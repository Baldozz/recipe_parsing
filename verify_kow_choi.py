import json
from src.parsers.jpeg_parser import parse_recipe_image

def test_kow_choi():
    img_path = "data/raw/jpg_recipes/20190828_183536.jpg"
    print(f"Testing parsing on: {img_path}")
    
    recipes = parse_recipe_image(img_path, previous_context=[])
    
    if not recipes:
        print("No recipes found.")
        return
        
    for r in recipes:
        print(json.dumps(r, indent=2))

if __name__ == "__main__":
    test_kow_choi()
