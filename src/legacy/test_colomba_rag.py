from src.query import answer_question
import sys

# Query specifically targeting the multi-stage nature
query = "Draft a complete guide to making Colomba. Include all stages: Refreshment, 1st Dough, and 2nd Dough. List ingredients and steps for each."

print(f"Query: {query}\n")
try:
    response = answer_question(query, "data/indices")
    print(f"RAG Response:\n{response}")
except Exception as e:
    print(f"Error: {e}")
