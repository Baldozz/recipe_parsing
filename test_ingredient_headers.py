import json
from src.parsers.jpeg_parser import parse_recipe_image

def main():
    image_path = "data/raw/jpg_recipes/20190828_185128.jpg"
    print(f"Testing parsing on {image_path} to check for ingredient headers...")
    
    try:
        recipes = parse_recipe_image(image_path)
        print(json.dumps(recipes, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
