from src.query import answer_question
import sys

def generate_menu():
    query = "Suggest a Chinese dinner menu with 5 dishes: 2 appetizers, 2 mains, and 1 dessert. Use only real recipes from the context."
    
    print(f"Querying: {query}...\n")
    
    response = answer_question(
        query=query,
        index_dir="data/indices",
        k=40  # Retrieve more docs to ensure variety (appetizers, mains, desserts)
    )
    
    print("--- MENU PROPOSAL ---")
    print(response)

if __name__ == "__main__":
    generate_menu()
