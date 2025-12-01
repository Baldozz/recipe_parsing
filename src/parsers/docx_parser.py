from pathlib import Path
from docx import Document
from src.parsers.text_parser import parse_recipe_text

def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def parse_recipe_docx(path: str, model: str | None = None) -> list[dict]:
    """
    Extract one or more recipes from a DOCX file.
    
    Returns:
        list[dict]: List of recipe dictionaries found in the document.
    """
    text = extract_text_from_docx(path)
    return parse_recipe_text(text, model=model)
