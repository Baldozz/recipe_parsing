from src.query import answer_question

INDEX_DIR = "data/index"

def generate_menu():
    print("🍽️ Generating Dinner Menu Options...\n")
    
    query = """
    I am a private chef and I need to create a 4-course dinner menu for 6 people.
    One of the guests is vegetarian, so please ensure there is a suitable vegetarian alternative for the main course, or that the main course is vegetarian-friendly.
    
    The client found the previous suggestions (Quiche, Meatballs, Cucumber Carpaccio, Rabbit Genovese) too generic.
    Please provide 3 NEW, DISTINCT menu options that are MORE ORIGINAL, CREATIVE, and EXCITING.
    Avoid standard/boring dishes. Look for interesting flavor combinations or less common ingredients in the database.
    
    Option 1: Budget-Friendly but Creative (Smart use of humble ingredients)
    Option 2: Mid-Range / Modern Bistro (Trendy, fresh, interesting techniques)
    Option 3: High-End / Gastronomic (Sophisticated, "wow" factor, premium ingredients)
    
    For EACH option, include the following 4 courses:
    1. Appetizer
    2. First Course (e.g., Pasta, Risotto, Soup - make it interesting!)
    3. Main Course (with vegetarian alternative/option)
    4. Dessert (MUST be included. If a perfect match isn't found, suggest the most interesting dessert available).
    
    For each dish in every menu:
    - Name the recipe exactly as it appears in the database.
    - Briefly describe it.
    - Explain why it is original/creative and fits the price range.
    
    Please present the output clearly, separated by Option.
    """
    
    try:
        # Using k=100 to get a deeper pool of recipes to find the "hidden gems"
        answer = answer_question(query, INDEX_DIR, k=100)
        print(answer)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_menu()
