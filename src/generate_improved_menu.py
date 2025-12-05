from src.query import retrieve, load_index, get_chat_client, CHAT_MODEL
import json

INDEX_DIR = "data/index"

def get_course_options(course_name, query, filters, docs, faiss_index, bm25, k=20):
    """
    Retrieve recipes for a specific course with filtering.
    """
    print(f"  🔍 Searching for {course_name} (Filter: {filters})...")
    results = retrieve(docs, faiss_index, bm25, query, k=k, filters=filters)
    
    context = ""
    for r in results:
        d = r["doc"]
        context += f"### {course_name}: {d['name']}\n{d['text']}\n\n"
    
    return context

def generate_improved_menu():
    print("🍽️ Generating Improved Dinner Menu (Query Decomposition + Filtering + Hybrid Search)...\n")
    
    faiss_index, bm25, docs = load_index(INDEX_DIR)
    
    # --- Step 1: Retrieve Candidates for Each Course ---
    
    # Appetizers
    appetizer_context = get_course_options(
        "Appetizer", 
        "Creative appetizer starter amuse-bouche", 
        {"dish_type": "Appetizer"}, # Matches "Starter / Appetizer" via partial match
        docs, faiss_index, bm25
    )
    
    # First Course
    first_course_context = get_course_options(
        "First Course", 
        "Pasta risotto soup interesting first course", 
        {}, # No strict dish_type filter as "First Course" isn't a standard tag, rely on query
        docs, faiss_index, bm25
    )
    
    # Main Course (General)
    main_context = get_course_options(
        "Main Course", 
        "Main course meat fish poultry", 
        {"dish_type": "Main Course"}, 
        docs, faiss_index, bm25
    )
    
    # Vegetarian Main
    veg_main_context = get_course_options(
        "Vegetarian Main", 
        "Vegetarian main course vegetable forward", 
        {"dish_type": "Main Course", "dietary": "Vegetarian"}, 
        docs, faiss_index, bm25
    )
    
    # Dessert
    dessert_context = get_course_options(
        "Dessert", 
        "Dessert sweet pastry cake ice cream", 
        {"dish_type": "Dessert"}, 
        docs, faiss_index, bm25
    )
    
    # --- Step 2: Synthesize Menu ---
    
    full_context = (
        appetizer_context + 
        first_course_context + 
        main_context + 
        veg_main_context + 
        dessert_context
    )
    
    print(f"  ✨ Context assembled. Generating menu with LLM...\n")
    
    client = get_chat_client()
    
    system_msg = """
    You are an expert private chef. Create a 4-course dinner menu for 6 people (1 vegetarian).
    You MUST use the provided recipes.
    """
    
    user_msg = f"""
    I need 3 DISTINCT menu options:
    1. Budget-Friendly / Rustic
    2. Mid-Range / Modern Bistro
    3. High-End / Gastronomic
    
    Structure for EACH option:
    1. Appetizer (Select from provided Appetizers)
    2. First Course (Select from provided First Courses)
    3. Main Course (Select from provided Mains) + Vegetarian Alternative (Select from provided Vegetarian Mains)
    4. Dessert (Select from provided Desserts)
    
    CRITICAL: 
    - Ensure the Vegetarian Alternative is actually vegetarian.
    - Ensure Desserts are actually desserts.
    - Do not repeat dishes across options if possible.
    
    Here are the available recipes:
    
    {full_context}
    """
    
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.4,
    )
    
    print(resp.choices[0].message.content)

if __name__ == "__main__":
    generate_improved_menu()
