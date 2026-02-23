from src.query import answer_question

def test_gemini_rag():
    print("🧪 Testing Gemini-only RAG with Metadata Filters...\n")
    
    # Check if we can find the dessert using explicit filters (proving classification)
    query = "How do I make Dou Hua?"
    filters = {
        "cuisine": "Chinese",
        "dish_type": "Dessert"
    }
    
    print(f"Query: {query}")
    print(f"Filters: {filters}\n")
    
    try:
        response = answer_question(
            query=query,
            index_dir="data/indices",
            filters=filters
        )
        print("--- RESPONSE ---")
        print(response)
        
        if "Dou Hua" in response and "Error" not in response:
            print("\n✅ SUCCESS: RAG is working with Gemini + Metadata!")
        else:
            print("\n⚠️ WARNING: Response did not contain expected content.")
            
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")

if __name__ == "__main__":
    test_gemini_rag()
