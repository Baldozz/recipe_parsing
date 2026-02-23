from src.query import answer_question
import time

INDEX_DIR = "data/indices"

def run_tests():
    print("🔥 Running Challenging RAG Tests...\n")
    
    challenges = [
        {
            "type": "Complex Constraint (Dietary + Cuisine + Course)",
            "query": "I need a 3-course Italian menu that is completely Gluten-Free. What do you suggest?"
        },
        {
            "type": "Ingredient Utilization (Leftovers)",
            "query": "I have a lot of leftover egg whites. Give me 3 recipes to use them up."
        },
        {
            "type": "Technique & Vibe (Molecular/Modern)",
            "query": "What is a good 'Amuse-bouche' that uses molecular gastronomy techniques (like siphons or gels)?"
        },
        {
            "type": "Specific Exclusion",
            "query": "What can I make with 'Jerusalem Artichoke' that is NOT a soup?"
        },
        {
            "type": "High Difficulty Search",
            "query": "Find me a 'Michelin level' main course that uses Duck."
        }
    ]
    
    for i, challenge in enumerate(challenges, 1):
        print(f"--- Test {i}: {challenge['type']} ---")
        print(f"Q: {challenge['query']}")
        start = time.time()
        try:
            answer = answer_question(challenge['query'], INDEX_DIR)
            elapsed = time.time() - start
            print(f"A: {answer}")
            print(f"[Time: {elapsed:.2f}s]\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    run_tests()
