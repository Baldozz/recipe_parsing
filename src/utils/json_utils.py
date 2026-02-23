def extract_json_from_text(text: str) -> str:
    """Strip markdown code fences from LLM output and return raw JSON string."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0]
    if "```" in text:
        return text.split("```")[1].split("```")[0]
    return text
