import json
import time
import google.generativeai as genai
from src.config import CHAT_MODEL
from src.utils.json_utils import extract_json_from_text

def detect_language(text: str) -> str:
    """
    Detect language using Gemini.
    Returns ISO 639-1 code (e.g., 'en', 'it', 'fr').
    """
    if not text or len(text) < 10:
        return 'en'
        
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"Detect the language of this text. Return ONLY the 2-letter ISO code (e.g. en, it, fr).\n\nText: {text[:200]}"
        )
        return response.text.strip().lower()[:2]
    except:
        return 'en'

def translate_recipe_to_english(recipe: dict) -> dict:
    """
    Translate a recipe dictionary to English using LLM.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Translate this recipe to English. Keep JSON structure.
        
        INPUT:
        {json.dumps(recipe, ensure_ascii=False)}
        
        OUTPUT JSON:
        """
        response = model.generate_content(prompt)
        return json.loads(extract_json_from_text(response.text))
    except Exception as e:
        print(f"Translation failed: {e}")
        return recipe

def create_bilingual_recipe(recipe: dict) -> tuple[dict, dict, str]:
    """
    Returns (original_recipe, english_recipe, detected_language).
    """
    # Detect language from name + steps
    sample_text = recipe.get('name', '') + " " + " ".join(recipe.get('steps', [])[:3])
    lang = detect_language(sample_text)
    
    recipe['language'] = lang
    
    if lang == 'en':
        return recipe, recipe, 'en'
    else:
        english_recipe = translate_recipe_to_english(recipe)
        english_recipe['language'] = 'en'
        english_recipe['translated_from'] = lang
        english_recipe['other_details'] = recipe.get('other_details', {})
        english_recipe['other_details']['original_language'] = lang
        
        return recipe, english_recipe, lang
