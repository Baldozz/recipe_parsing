from pathlib import Path
import os
import json
import re

from .parsers.jpeg_parser import parse_recipe_image
from .parsers.docx_parser import parse_recipe_docx
from .parsers.excel_parser import parse_excel_file
from .parsers.recipe_deduplicator import is_duplicate
from .parsers.recipe_translator import create_bilingual_recipe


def sanitize_filename(name: str) -> str:
    """
    Convert a recipe name into a safe filename.
    
    Examples:
        "Chocolate Chip Cookies" -> "chocolate_chip_cookies"
        "Pasta Carbonara (Part 1)" -> "pasta_carbonara_part_1"
        "Mom's Best Pie!" -> "moms_best_pie"
    """
    # Convert to lowercase
    name = name.lower()
    # Replace spaces and hyphens with underscores
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove special characters, keep only alphanumeric and underscores
    name = re.sub(r'[^a-z0-9_]', '', name)
    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    # If empty after sanitization, use a default
    if not name:
        name = "recipe"
    return name


def get_unique_filename(output_dir: str, base_name: str, extension: str = ".json") -> str:
    """
    Generate a unique filename by appending a counter if the file already exists.
    
    Args:
        output_dir: Directory where file will be saved
        base_name: Base filename (without extension)
        extension: File extension (default: .json)
    
    Returns:
        Unique filename
    """
    output_path = Path(output_dir) / f"{base_name}{extension}"
    
    if not output_path.exists():
        return f"{base_name}{extension}"
    
    # File exists, add counter
    counter = 2
    while True:
        new_name = f"{base_name}_{counter}{extension}"
        output_path = Path(output_dir) / new_name
        if not output_path.exists():
            return new_name
        counter += 1


def save_recipe_bilingual(recipe: dict, output_dir: str, base_filename: str) -> tuple[str, str, str]:
    """
    Save a recipe in both its original language and English.
    
    Args:
        recipe: Recipe dictionary
        output_dir: Directory to save files
        base_filename: Base filename (without extension or language suffix)
    
    Returns:
        Tuple of (original_filename, english_filename, language_code)
    """
    # Create bilingual versions
    original_recipe, english_recipe, language = create_bilingual_recipe(recipe)
    
    # Determine filenames
    if language == "en":
        # If already English, save only one file
        filename = get_unique_filename(output_dir, f"{base_filename}_parsed")
        filepath = Path(output_dir) / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(english_recipe, indent=2, fp=f, ensure_ascii=False)
        
        return filename, filename, language
    else:
        # Save both original and English versions
        original_filename = get_unique_filename(output_dir, f"{base_filename}_{language}_parsed")
        english_filename = get_unique_filename(output_dir, f"{base_filename}_en_parsed")
        
        original_path = Path(output_dir) / original_filename
        english_path = Path(output_dir) / english_filename
        
        with open(original_path, "w", encoding="utf-8") as f:
            json.dump(original_recipe, indent=2, fp=f, ensure_ascii=False)
        
        with open(english_path, "w", encoding="utf-8") as f:
            json.dump(english_recipe, indent=2, fp=f, ensure_ascii=False)
        
        return original_filename, english_filename, language


def load_existing_recipes(output_dir: str) -> list[dict]:
    """
    Load all existing parsed recipes from the output directory.
    
    Args:
        output_dir: Directory containing parsed recipe JSON files
    
    Returns:
        List of recipe dictionaries
    """
    existing_recipes = []
    output_path = Path(output_dir)
    
    if not output_path.exists():
        return existing_recipes
    
    for json_file in output_path.glob("*_parsed.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                recipe = json.load(f)
                existing_recipes.append(recipe)
        except Exception:
            # Skip files that can't be loaded
            pass
    
    return existing_recipes


def ingest_images(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o", skip_duplicates: bool = True) -> None:
    """
    Process all recipe images in a folder.
    Each image may contain multiple recipes, which will be saved as separate files.
    
    Args:
        input_dir: Directory containing image files
        output_dir: Directory to save parsed recipes
        model: LLM model to use for parsing
        skip_duplicates: If True, skip recipes that are duplicates of existing ones
    """
    os.makedirs(output_dir, exist_ok=True)

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    input_path = Path(input_dir)
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"No image files found in {input_dir}")
        return

    print(f"Found {len(image_files)} recipe images\n")
    
    # Load existing recipes for duplicate detection
    existing_recipes = []
    if skip_duplicates:
        print("Loading existing recipes for duplicate detection...")
        existing_recipes = load_existing_recipes(output_dir)
        print(f"Found {len(existing_recipes)} existing recipes\n")

    # Load processing history to resume if interrupted
    processed_files = set()
    results = []
    total_recipes = 0
    duplicates_skipped = 0
    
    summary_path = Path(output_dir) / "_processing_summary_images.json"
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                for entry in history:
                    if entry.get("status") == "success":
                        processed_files.add(entry.get("source_file"))
            print(f"Resuming: Found {len(processed_files)} already processed files")
            # Initialize results with history so we don't lose previous records
            results = history
        except Exception as e:
            print(f"Warning: Could not load processing history: {e}")

    for i, image_file in enumerate(image_files, 1):
        if image_file.name in processed_files:
            print(f"[{i}/{len(image_files)}] Skipping {image_file.name} (already processed)")
            continue

        print(f"[{i}/{len(image_files)}] Processing: {image_file.name}")

        try:
            recipes = parse_recipe_image(str(image_file), model=model)
            
            if not recipes:
                print(f"Warning: No recipes found in {image_file.name}\n")
                results.append({
                    "source_file": image_file.name,
                    "status": "warning",
                    "message": "No recipes found"
                })
                continue

            print(f"Found {len(recipes)} recipe(s) in this image")

            for recipe in recipes:
                recipe_name = recipe.get("name", "unknown_recipe")
                
                # Check for duplicates
                is_dup = False
                if skip_duplicates and existing_recipes:
                    for existing_recipe in existing_recipes:
                        if is_duplicate(recipe, existing_recipe):
                            is_dup = True
                            print(f"  ⊘ {recipe_name} (duplicate, skipped)")
                            duplicates_skipped += 1
                            results.append({
                                "source_file": image_file.name,
                                "status": "duplicate",
                                "recipe_name": recipe_name,
                                "message": "Skipped - duplicate of existing recipe"
                            })
                            break
                
                if is_dup:
                    continue
                
                # Save the recipe in both original and English
                sanitized_name = sanitize_filename(recipe_name)
                original_file, english_file, language = save_recipe_bilingual(
                    recipe, output_dir, sanitized_name
                )

                # Report saved files
                if language == "en":
                    print(f"  ✓ {recipe_name} -> {original_file}")
                    results.append({
                        "source_file": image_file.name,
                        "output_file": original_file,
                        "status": "success",
                        "recipe_name": recipe_name,
                        "language": language
                    })
                else:
                    print(f"  ✓ {recipe_name} ({language}) -> {original_file}, {english_file}")
                    results.append({
                        "source_file": image_file.name,
                        "output_file_original": original_file,
                        "output_file_english": english_file,
                        "status": "success",
                        "recipe_name": recipe_name,
                        "language": language
                    })
                
                total_recipes += 1
                
                # Add to existing recipes for subsequent duplicate checks
                if skip_duplicates:
                    existing_recipes.append(recipe)


            print()

            # Periodic save of summary (every 10 images) to allow resuming
            if i % 10 == 0:
                summary_path = Path(output_dir) / "_processing_summary_images.json"
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(results, indent=2, fp=f, ensure_ascii=False)

        except Exception as e:
            print(f"Error: {e}\n")
            results.append({
                "source_file": image_file.name,
                "status": "error",
                "error": str(e),
            })

    summary_path = Path(output_dir) / "_processing_summary_images.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"Image processing complete: {successful} recipes from {len(image_files)} images")
    if duplicates_skipped > 0:
        print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


def ingest_docx(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o", skip_duplicates: bool = True) -> None:
    """
    Process all DOCX recipe files in a folder.
    Each document may contain multiple recipes, which will be saved as separate files.
    
    Args:
        input_dir: Directory containing DOCX files
        output_dir: Directory to save parsed recipes
        model: LLM model to use for parsing
        skip_duplicates: If True, skip recipes that are duplicates of existing ones
    """
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(input_dir)
    docx_files = [f for f in input_path.iterdir() if f.suffix.lower() == ".docx"]

    if not docx_files:
        print(f"No .docx files found in {input_dir}")
        return

    print(f"Found {len(docx_files)} DOCX recipe files\n")
    
    # Load existing recipes for duplicate detection
    existing_recipes = []
    if skip_duplicates:
        print("Loading existing recipes for duplicate detection...")
        existing_recipes = load_existing_recipes(output_dir)
        print(f"Found {len(existing_recipes)} existing recipes\n")

    results = []
    total_recipes = 0
    duplicates_skipped = 0

    for i, docx_file in enumerate(docx_files, 1):
        print(f"[{i}/{len(docx_files)}] Processing: {docx_file.name}")
        try:
            recipes = parse_recipe_docx(str(docx_file), model=model)
            
            if not recipes:
                print(f"Warning: No recipes found in {docx_file.name}\n")
                results.append({
                    "source_file": docx_file.name,
                    "status": "warning",
                    "message": "No recipes found"
                })
                continue

            print(f"Found {len(recipes)} recipe(s) in this document")

            for recipe in recipes:
                recipe_name = recipe.get("name", "unknown_recipe")
                
                # Check for duplicates
                is_dup = False
                if skip_duplicates and existing_recipes:
                    for existing_recipe in existing_recipes:
                        if is_duplicate(recipe, existing_recipe):
                            is_dup = True
                            print(f"  ⊘ {recipe_name} (duplicate, skipped)")
                            duplicates_skipped += 1
                            results.append({
                                "source_file": docx_file.name,
                                "status": "duplicate",
                                "recipe_name": recipe_name,
                                "message": "Skipped - duplicate of existing recipe"
                            })
                            break
                
                if is_dup:
                    continue
                
                # Save the recipe in both original and English
                sanitized_name = sanitize_filename(recipe_name)
                original_file, english_file, language = save_recipe_bilingual(
                    recipe, output_dir, sanitized_name
                )

                # Report saved files
                if language == "en":
                    print(f"  ✓ {recipe_name} -> {original_file}")
                    results.append({
                        "source_file": docx_file.name,
                        "output_file": original_file,
                        "status": "success",
                        "recipe_name": recipe_name,
                        "language": language
                    })
                else:
                    print(f"  ✓ {recipe_name} ({language}) -> {original_file}, {english_file}")
                    results.append({
                        "source_file": docx_file.name,
                        "output_file_original": original_file,
                        "output_file_english": english_file,
                        "status": "success",
                        "recipe_name": recipe_name,
                        "language": language
                    })
                
                total_recipes += 1
                
                # Add to existing recipes for subsequent duplicate checks
                if skip_duplicates:
                    existing_recipes.append(recipe)

            print()

        except Exception as e:
            print(f"Error: {e}\n")
            results.append({
                "source_file": docx_file.name,
                "status": "error",
                "error": str(e),
            })

    summary_path = Path(output_dir) / "_processing_summary_docx.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"DOCX processing complete: {successful} recipes from {len(docx_files)} documents")
    if duplicates_skipped > 0:
        print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


def ingest_excel(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o", skip_duplicates: bool = True) -> None:
    """
    Process all Excel files in a folder.
    Each sheet may contain multiple recipes, which will be saved as separate files.
    
    Args:
        input_dir: Directory containing Excel files
        output_dir: Directory to save parsed recipes
        model: LLM model to use for parsing
        skip_duplicates: If True, skip recipes that are duplicates of existing ones
    """
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(input_dir)
    xlsx_files = [f for f in input_path.iterdir() if f.suffix.lower() in {".xlsx", ".xls"}]

    if not xlsx_files:
        print(f"No Excel files found in {input_dir}")
        return

    print(f"Found {len(xlsx_files)} Excel files\n")
    
    # Load existing recipes for duplicate detection
    existing_recipes = []
    if skip_duplicates:
        print("Loading existing recipes for duplicate detection...")
        existing_recipes = load_existing_recipes(output_dir)
        print(f"Found {len(existing_recipes)} existing recipes\n")

    results = []
    total_recipes = 0
    duplicates_skipped = 0

    for i, xlsx_file in enumerate(xlsx_files, 1):
        print(f"[{i}/{len(xlsx_files)}] Processing: {xlsx_file.name}")
        try:
            for sheet_idx, (sheet_name, recipes) in enumerate(parse_excel_file(str(xlsx_file), model=model)):
                # parse_excel_file returns (sheet_name, recipe_dict)
                # We need to handle the case where it might return a single recipe or multiple
                
                # Wrap single recipe in list if needed
                if isinstance(recipes, dict):
                    recipes = [recipes]
                
                print(f"  Sheet '{sheet_name}': Found {len(recipes)} recipe(s)")
                
                for recipe in recipes:
                    recipe_name = recipe.get("name", "unknown_recipe")
                    
                    # Check for duplicates
                    is_dup = False
                    if skip_duplicates and existing_recipes:
                        for existing_recipe in existing_recipes:
                            if is_duplicate(recipe, existing_recipe):
                                is_dup = True
                                print(f"    ⊘ {recipe_name} (duplicate, skipped)")
                                duplicates_skipped += 1
                                results.append({
                                    "source_file": xlsx_file.name,
                                    "sheet": sheet_name,
                                    "status": "duplicate",
                                    "recipe_name": recipe_name,
                                    "message": "Skipped - duplicate of existing recipe"
                                })
                                break
                    
                    if is_dup:
                        continue
                    
                    # Save the recipe in both original and English
                    sanitized_name = sanitize_filename(recipe_name)
                    original_file, english_file, language = save_recipe_bilingual(
                        recipe, output_dir, sanitized_name
                    )

                    # Report saved files
                    if language == "en":
                        print(f"    ✓ {recipe_name} -> {original_file}")
                        results.append({
                            "source_file": xlsx_file.name,
                            "sheet": sheet_name,
                            "output_file": original_file,
                            "status": "success",
                            "recipe_name": recipe_name,
                            "language": language
                        })
                    else:
                        print(f"    ✓ {recipe_name} ({language}) -> {original_file}, {english_file}")
                        results.append({
                            "source_file": xlsx_file.name,
                            "sheet": sheet_name,
                            "output_file_original": original_file,
                            "output_file_english": english_file,
                            "status": "success",
                            "recipe_name": recipe_name,
                            "language": language
                        })
                    
                    total_recipes += 1
                    
                    # Add to existing recipes for subsequent duplicate checks
                    if skip_duplicates:
                        existing_recipes.append(recipe)

            print()

        except Exception as e:
            print(f"Error in {xlsx_file.name}: {e}\n")
            results.append({
                "source_file": xlsx_file.name,
                "status": "error",
                "error": str(e),
            })

    summary_path = Path(output_dir) / "_processing_summary_excel.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"Excel processing complete: {successful} recipes from {len(xlsx_files)} files")
    if duplicates_skipped > 0:
        print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


