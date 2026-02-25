import os
from pathlib import Path
import google.generativeai as genai

from src.query import load_index, retrieve, MAX_CHARS_PER_DOC, MAX_TOTAL_CHARS, _truncate_for_prompt
from src.utils.retry import call_model_with_retry
import json
import random

# Removed strictly-typed extraction to prevent over-filtering.
# Relying purely on FAISS / BM25 semantic hybrid search instead.

def generate_menu(query: str, recipe_index_dir: str, menu_index_dir: str, style_guide_path: str, base_url: str = ""):
    """Generate menus based on past menus, style guide, and available recipes."""
    
    # 1. Load Style Guide
    style_guide = ""
    if Path(style_guide_path).exists():
        with open(style_guide_path, "r", encoding="utf-8") as f:
            style_guide = f.read()
    else:
        print(f"Warning: Style guide not found at {style_guide_path}")

    # 2. Retrieve Past Menus
    print("Searching past menus for inspiration...")
    menu_faiss, menu_bm25, menu_docs = load_index(menu_index_dir)
    retrieved_menus = retrieve(menu_docs, menu_faiss, menu_bm25, query, k=10)
    
    menu_context_blocks = []
    for r in retrieved_menus:
        d = r["doc"]
        raw = d.get("raw", {})
        source = raw.get("filename", "Unknown Menu PDF")
        block = f"### Past Menu: {d['name']} (Source: {source})\n{d['text']}"
        menu_context_blocks.append(_truncate_for_prompt(block, MAX_CHARS_PER_DOC))
    past_menus_text = "\n\n".join(menu_context_blocks)

    # 3. Retrieve Recipes using Multi-Stage Semantic Search
    print("Searching recipes database by course category...")
    recipe_faiss, recipe_bm25, recipe_docs = load_index(recipe_index_dir)
    
    categories = [
        "Appetizer Starter",
        "Main Course",
        "Dessert Sweet"
    ]
    
    retrieved_recipes = []
    # Use a dictionary to avoid appending duplicate recipes from different searches
    unique_recipes = {}
    
    for cat in categories:
        # We append only the category directly to the user's query so the cuisine remains the strongest signal
        cat_query = f"{query} {cat}"
        # Pull a much larger pool of recipes (k=30 per category) to guarantee variety 
        res = retrieve(recipe_docs, recipe_faiss, recipe_bm25, cat_query, k=30)
        for r in res:
            recipe_id = r["doc"]["id"]
            if recipe_id not in unique_recipes:
                unique_recipes[recipe_id] = r
                
    retrieved_recipes = list(unique_recipes.values())
    # Shuffle to introduce variety and prevent the exact same recipes from always appearing at the top
    random.shuffle(retrieved_recipes)
    
    recipe_context_blocks = []
    total_len = len(past_menus_text) + len(style_guide)
    
    for r in retrieved_recipes:
        d = r["doc"]
        raw = d.get("raw", {})
        source_files = raw.get("source_files", [])
        source_meta = raw.get("source_metadata", {})
        source_filename = source_meta.get("filename", "")
        source_path = source_meta.get("path", "")
        
        source = "Unknown source file"
        markdown_link = ""
        if base_url:
            import urllib.parse
            import re
            
            # The id is typically the stem of the original JSON file.
            recipe_id = d["id"]
            
            # Use urllib.parse.quote for spaces and special characters.
            json_url = f"{base_url}/api/recipe/{urllib.parse.quote(recipe_id)}"
            
            display_name = source_filename or d['name']
            markdown_link = f"[View Recipe JSON]({json_url})"
            source = display_name
        elif source_files:
            source = ", ".join(source_files)
        elif source_filename:
            source = source_filename

        if markdown_link:
            block = f"### Recipe: {d['name']} {markdown_link}\nOriginal File: {source}\n{d['text']}"
        else:
            block = f"### Recipe: {d['name']}\nOriginal File: {source}\n{d['text']}"

        block = _truncate_for_prompt(block, MAX_CHARS_PER_DOC)
        
        # Ensure we do not blow past the context window limits
        if total_len + len(block) > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total_len
            if remaining <= 0:
                break
            block = block[:remaining] + "\n...[truncated]"
            
        recipe_context_blocks.append(block)
        total_len += len(block)
    
    recipes_text = "\n\n".join(recipe_context_blocks)

    # 4. Generate with Gemini
    print("Generating your menus (this might take a moment)...")
    genai_model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""
    You are an expert Private Chef AI. Your task is to design exactly 3 cohesive, elegant multi-course menus based on the user's request.
    
    USER REQUEST: {query}
    
    === CHEF'S STYLE GUIDE (Your culinary fingerprint) ===
    {style_guide}
    
    === PAST MENU INSPIRATIONS (Use these to understand flow and structure) ===
    {past_menus_text}
    
    === AVAILABLE RECIPES (You must only use these building blocks) ===
    {recipes_text}
    
    ---
    INSTRUCTIONS:
    1. Read the user's request carefully.
    2. Review the Chef's Style Guide to ensure the menus match the chef's culinary philosophy, structure, flavor pairings, and aesthetic.
    3. Look at Past Menu Inspirations to get a feel for course combinations and pacing.
    4. Construct EXACTLY 3 distinct menu options using ONLY the 'Available Recipes' provided. Do not hallucinate external dishes.
    5. Each menu should have a clear progression of courses (e.g., Starters, Main Course, Dessert) depending on the request and your style guide.
    6. Make the menus sound highly professional and elegant. Format the output beautifully in Markdown.
    7. For each menu, provide a short 1-sentence description of the concept/theme, followed by the courses.
    8. VERY IMPORTANT LINKING RULE: Next to EACH dish you list in the menus, you MUST paste the exact `[View Recipe JSON](...)` markdown link exactly as it is provided next to the Recipe's name in the `AVAILABLE RECIPES` text. Do not omit the link, and do not modify the URL inside it!
    """

    try:
        # Pass stream=True to the model
        response = call_model_with_retry(genai_model, prompt, stream=True)
        return response
    except Exception as e:
        return f"Error generating menu: {e}"
