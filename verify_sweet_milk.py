import json
from src.parsers.jpeg_parser import parse_recipe_image

def test_sweet_milk():
    img_path = "data/raw/test_sweet_milk.jpg"
    print(f"Testing parsing on: {img_path}")
    
    recipes = parse_recipe_image(img_path, previous_context=[])
    
    if not recipes:
        print("No recipes found.")
        return
        
    for r in recipes:
        print(json.dumps(r, indent=2))

if __name__ == "__main__":
    test_sweet_milk()
