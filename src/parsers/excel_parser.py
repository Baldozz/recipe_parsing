from pathlib import Path
import pandas as pd
from src.parsers.text_parser import parse_recipe_text

def parse_excel_sheet(df: pd.DataFrame, sheet_name: str, file_name: str, model: str | None = None) -> dict:
    table_str = df.to_markdown(index=False)
    text = f"""File: {file_name}
Sheet: {sheet_name}

Table:
{table_str}
"""
    return parse_recipe_text(text, model=model)

def parse_excel_file(path: str, model: str | None = None) -> list[tuple[str, dict]]:
    xls = pd.read_excel(path, sheet_name=None)
    recipes = []
    for idx, (sheet_name, df) in enumerate(xls.items()):
        recipe = parse_excel_sheet(df, sheet_name, Path(path).name, model=model)
        recipes.append((sheet_name, recipe))
    return recipes
