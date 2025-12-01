import json
import sys
import os

# Add current directory to path so we can import src
sys.path.append(os.getcwd())

from src.parsers.jpeg_parser import parse_recipe_image

def main():
    images = [
        "data/raw/jpg_recipes/Image(106).jpeg"
    ]
    
    for image_path in images:
        print(f"\n--- Testing parsing on {image_path} ---")
        try:
            recipes = parse_recipe_image(image_path)
            print(json.dumps(recipes, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error parsing image: {e}")

if __name__ == "__main__":
    main()
