"""
Recipe translation module for converting recipes to English.

This module provides functionality to:
1. Detect the language of a recipe
2. Translate recipes to English
3. Preserve original recipe data
"""

import json
from src.config import get_chat_client, CHAT_MODEL


def detect_language(recipe: dict) -> str:
    """
    Detect the language of a recipe.
    
    Args:
        recipe: Recipe dictionary
    
    Returns:
        Language code (e.g., 'en', 'it', 'es', 'fr', 'de')
    """
    client = get_chat_client()
    
    # Sample text from recipe for language detection
    sample_text = f"{recipe.get('name', '')} {' '.join(recipe.get('ingredients', [])[:3])}"
    
    prompt = f"""Detect the language of this recipe text and return ONLY the ISO 639-1 language code (2 letters).

Examples:
- English: en
- Italian: it
- Spanish: es
- French: fr
- German: de
- Portuguese: pt

Recipe text: {sample_text}

Return ONLY the 2-letter language code, nothing else."""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a language detection assistant. Return only ISO 639-1 language codes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=10
    )
    
    content = response.choices[0].message.content
    if not content:
        return "en"
    lang_code = content.strip().lower()
    
    # Validate it's a 2-letter code
    if len(lang_code) == 2 and lang_code.isalpha():
        return lang_code
    
    # Default to English if detection fails
    return "en"


def translate_recipe_to_english(recipe: dict, source_language: str = None) -> dict:
    """
    Translate a recipe to English.
    
    Args:
        recipe: Recipe dictionary to translate
        source_language: Optional source language code (auto-detected if not provided)
    
    Returns:
        Translated recipe dictionary
    """
    # Detect language if not provided
    if source_language is None:
        source_language = detect_language(recipe)
    
    # If already in English, return as-is
    if source_language == "en":
        return recipe
    
    client = get_chat_client()
    
    # Prepare recipe for translation
    recipe_json = json.dumps(recipe, ensure_ascii=False, indent=2)
    
    prompt = f"""Translate this recipe from {source_language} to English. 

IMPORTANT:
1. Translate the recipe name, ingredients, steps, and all text in other_details
2. Keep the same JSON structure
3. Preserve measurements and numbers exactly as they are
4. Use natural, fluent English
5. Keep cooking terminology accurate

Original recipe (in {source_language}):
{recipe_json}

Return ONLY the translated JSON, nothing else."""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional recipe translator. Translate recipes accurately while preserving structure and measurements."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    translated_recipe = json.loads(response.choices[0].message.content)
    
    # Add metadata about translation
    if "other_details" not in translated_recipe:
        translated_recipe["other_details"] = {}
    
    translated_recipe["other_details"]["translated_from"] = source_language
    translated_recipe["other_details"]["original_language"] = source_language
    
    return translated_recipe


def create_bilingual_recipe(recipe: dict) -> tuple[dict, dict, str]:
    """
    Create both original and English versions of a recipe.
    
    Args:
        recipe: Original recipe dictionary
    
    Returns:
        Tuple of (original_recipe, english_recipe, language_code)
    """
    # Detect language
    language = detect_language(recipe)
    
    # Add language metadata to original
    original_recipe = recipe.copy()
    if "other_details" not in original_recipe:
        original_recipe["other_details"] = {}
    original_recipe["other_details"]["language"] = language
    
    # Translate to English if needed
    if language == "en":
        english_recipe = original_recipe
    else:
        english_recipe = translate_recipe_to_english(recipe, language)
    
    return original_recipe, english_recipe, language
