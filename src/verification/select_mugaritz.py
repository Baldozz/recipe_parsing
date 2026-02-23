from src.query import answer_question

def find_complex_mugaritz():
    print("🔍 Searching for Complex Mugaritz Recipes...\n")
    
    # We ask the LLM to select specific ones, but we also pass a filter if possible.
    # Since "Mugaritz" isn't a strict metadata field (unless in 'cuisine' or 'source'), we query for it.
    # We prioritize Level 3 via the prompt context or by trying a specific filtered query first.
    
    query = """
    Identify 5 distinct recipes from Mugaritz that are the most technically complex (Level 3 / Michelin style).
    Briefly explain WHY each is complex (e.g. requires specialized equipment, long prep time, molecular techniques).
    Select strictly from the provided context.
    """
    
    # We'll try to nudge the retrieval by asking for "Mugaritz" key terms
    # and we can try to pass a difficulty filter if we are confident, 
    # but "Mugaritz" recipes might index as "Spanish" or "Modernist". 
    # Let's rely on the semantic search for "Mugaritz complex Level 3" headers first.
    
    # But to be precise, let's use the filter for Level 3 if possible in the retrieval?
    # Actually, RAG retrieval combines BM25+Vector. 
    # Let's just run a strong query.
    
    response = answer_question(
        query=query,
        index_dir="data/indices",
        k=50, # Retrieve a lot of candidates to find the specific "Mugaritz" ones
    )
    
    print("--- MUGARITZ SELECTION ---")
    print(response)

if __name__ == "__main__":
    find_complex_mugaritz()
