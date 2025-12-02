import json
from src.stitch_recipes import merge_recipes

def main():
    # Simulate 3 parts of the Colomba recipe
    parts = [
        {
            "name": "Colombe (1° impasto)",
            "ingredients": ["Flour", "Water", "Yeast"],
            "steps": ["Mix flour and water", "Let rest"],
            "source_metadata": {"filename": "img1.jpg"}
        },
        {
            "name": "Colombe (2° impasto)",
            "ingredients": ["Sugar", "Butter", "Egg Yolks"],
            "steps": ["Add sugar and butter", "Knead well"],
            "source_metadata": {"filename": "img2.jpg"}
        },
        {
            "name": "Colombe (Glaçage)",
            "ingredients": ["Almonds", "Sugar", "Egg Whites"],
            "steps": ["Mix almonds and sugar", "Spread on top"],
            "source_metadata": {"filename": "img3.jpg"}
        }
    ]

    print("--- Merging Colomba Recipe Parts ---")
    merged = merge_recipes(parts)
    
    print(json.dumps(merged, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
