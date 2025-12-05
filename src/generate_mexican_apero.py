from src.query import answer_question

INDEX_DIR = "data/index"

def generate_menu():
    print("🌮 Generating Mexican Apero Menu...\n")
    
    query = """
    I need a Mexican-inspired 'Apero' (Appetizer/Snack) menu for 6 friends.
    Please suggest 5 distinct items (finger foods, dips, or small plates) and 1 drink pairing.
    
    Focus on:
    - Sharing style
    - Fresh flavors (Lime, Coriander, Chili)
    - A mix of textures (Crispy, Creamy, Fresh)
    
    For each item:
    1. Name the recipe exactly as it appears in the database.
    2. Briefly describe it.
    3. Explain why it works for an apero.
    
    If you find 'Guacamole', definitely include it!
    """
    
    try:
        # We use a larger k to ensure we get enough variety
        answer = answer_question(query, INDEX_DIR, k=30)
        print(answer)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_menu()
