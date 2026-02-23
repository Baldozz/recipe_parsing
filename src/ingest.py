from pathlib import Path
import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from src.config import CHAT_MODEL
from src.parsers.docx_parser import parse_recipe_docx
from src.parsers.excel_parser import parse_excel_file
from src.parsers.jpeg_parser import parse_recipe_image
from src.parsers.multimodal_parser import parse_session
from src.parsers.recipe_deduplicator import is_duplicate
from src.parsers.recipe_merger import detect_recipe_part, merge_recipe_parts
from src.parsers.recipe_translator import create_bilingual_recipe
from src.utils.image_grouper import ImageGrouper


def sanitize_filename(name: str) -> str:
    """
    Convert a recipe name into a safe filename.
    
    Examples:
        "Chocolate Chip Cookies" -> "chocolate_chip_cookies"
        "Pasta Carbonara (Part 1)" -> "pasta_carbonara_part_1"
        "Mom's Best Pie!" -> "moms_best_pie"
    """
    if not name:
        return "recipe"
    # Convert to lowercase
    name = str(name).lower()
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


def process_group_worker(group_data):
    group, output_dir, model, skip_duplicates, existing_recipes = group_data
    group_id = group[0].name
    results = []
    
    try:
        group_paths = [str(p) for p in group]
        recipes = parse_session(group_paths, model=model)
        
        if not recipes:
            return [{
                "group_id": group_id,
                "source_files": [f.name for f in group],
                "status": "warning",
                "message": "No recipes found"
            }]

        for recipe in recipes:
            # Inject metadata
            recipe["source_metadata"] = {
                "source_files": [f.name for f in group],
                "group_id": group_id,
                "type": "image_group"
            }

            recipe_name = recipe.get("name", "unknown_recipe")
            
            # Check for duplicates
            is_dup = False
            if skip_duplicates and existing_recipes:
                for existing_recipe in existing_recipes:
                    if is_duplicate(recipe, existing_recipe):
                        is_dup = True
                        break
            
            if is_dup:
                results.append({
                    "group_id": group_id,
                    "status": "duplicate",
                    "recipe_name": recipe_name,
                    "message": "Skipped - duplicate"
                })
                continue

            # Save using helper
            sanitized_name = sanitize_filename(recipe_name)
            original_file, english_file, language = save_recipe_bilingual(
                recipe, output_dir, sanitized_name
            )
            
            results.append({
                "group_id": group_id,
                "status": "success",
                "recipe_name": recipe_name,
                "language": language,
                "output_file": original_file if language == "en" else f"{original_file}, {english_file}"
            })
            
    except Exception as e:
        results.append({
            "group_id": group_id,
            "status": "error",
            "message": str(e)
        })
        
    time.sleep(2) # Minimal throttling for Flash
    return results


def ingest_images(input_dir: str, output_dir: str = "data/parsed", model: str = CHAT_MODEL, skip_duplicates: bool = True) -> None:
    """
    Process all recipe images in a folder.
    Images are GROUPED by timestamp/sequence to handle multi-page recipes.
    
    Args:
        input_dir: Directory containing image files
        output_dir: Directory to save parsed recipes
        model: LLM model to use for parsing (default: configured CHAT_MODEL)
        skip_duplicates: If True, skip recipes that are duplicates of existing ones
    """
    os.makedirs(output_dir, exist_ok=True)

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    input_path = Path(input_dir)
    # Get all image files
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"No image files found in {input_dir}")
        return

    print(f"Found {len(image_files)} images. Grouping by timestamp...")
    
    # GROUP IMAGES
    grouper = ImageGrouper(time_gap_threshold_seconds=60)  # max_group_size defaults to 8
    image_groups = grouper.group_images(image_files)
    
    grouper.print_grouping_summary(image_groups)
    print(f"Total Groups to Process: {len(image_groups)}")
    print(f"Process ID: {os.getpid()}\n")
    
    # Load existing recipes for duplicate detection
    existing_recipes = []
    if skip_duplicates:
        print("Loading existing recipes for duplicate detection...")
        existing_recipes = load_existing_recipes(output_dir)
        print(f"Found {len(existing_recipes)} existing recipes\n")

    # Load processing history
    processed_groups = set()
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
                        processed_groups.add(entry.get("group_id"))
            print(f"Resuming: Found {len(processed_groups)} already processed groups")
            results = history
        except Exception as e:
            print(f"Warning: Could not load processing history: {e}")

    # PARALLEL EXECUTION
    max_workers = 1
    print(f"Starting parallel processing with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = []
        for group in image_groups:
            group_id = group[0].name
            if group_id in processed_groups:
                continue
            
            # Package args
            args = (group, output_dir, model, skip_duplicates, existing_recipes)
            futures.append(executor.submit(process_group_worker, args))
            
        # Process results as they complete
        if futures:
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Groups"):
                #time.sleep(5)
                try:
                    group_results = future.result()
                    results.extend(group_results)
                    # Check for successes
                    for res in group_results:
                        if res.get("status") == "success":
                            total_recipes += 1
                            if "output_file" in res:
                                print(f"  ✓ {res.get('recipe_name')} -> {res.get('output_file')}")
                            else:
                                print(f"  ✓ {res.get('recipe_name')} ({res.get('language')})")
                        elif res.get("status") == "duplicate":
                            duplicates_skipped += 1
                        elif res.get("status") == "error":
                            print(f"  ✗ Error: {res.get('message')}")
                            
                    # Periodic save
                    if len(results) % 20 == 0:
                         with open(summary_path, "w", encoding="utf-8") as f:
                            json.dump(results, indent=2, fp=f, ensure_ascii=False)

                except Exception as e:
                    print(f"  ✗ Fatal Worker Error: {e}")

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    # --- Post-processing passes ---
    _resolve_related_to(output_dir)
    _merge_name_parts(output_dir)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"Image processing complete: {successful} recipes from {len(image_groups)} groups")
    if duplicates_skipped > 0:
        print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


def _normalize(name) -> str:
    """Lowercase, strip, remove non-alphanumeric for fuzzy name matching."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(name).lower().strip())


def _resolve_related_to(output_dir: str) -> None:
    """
    Merge any recipe that has a `related_to` field into its named parent.

    This handles the case where the LLM correctly identified a component
    (e.g. "Duck Sauce", related_to="Duck Breast") but saved it as a
    separate file.  After merging, the child file is deleted.
    """
    print("\n--- Post-processing: resolving related_to links ---")
    parsed_dir = Path(output_dir)
    file_map: dict[Path, dict] = {}

    for f in parsed_dir.glob("*_parsed.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            file_map[f] = data
        except Exception:
            pass

    # Build lookup: normalised name → (path, data)
    name_index: dict[str, tuple[Path, dict]] = {}
    for f, data in file_map.items():
        norm = _normalize(data.get("name", ""))
        if norm:
            name_index[norm] = (f, data)

    merged_count = 0
    for child_path, child in list(file_map.items()):
        related = child.get("related_to")
        if not related:
            continue

        norm_parent = _normalize(related)
        if norm_parent not in name_index:
            continue  # parent not found — leave as-is

        parent_path, parent = name_index[norm_parent]
        if parent_path == child_path:
            continue  # self-reference guard

        print(f"  Merging '{child.get('name')}' → '{parent.get('name')}' (related_to)")
        parent.setdefault("ingredients", []).extend(child.get("ingredients", []))
        parent.setdefault("steps", []).extend(child.get("steps", []))

        with open(parent_path, "w", encoding="utf-8") as fp:
            json.dump(parent, fp, indent=2, ensure_ascii=False)

        os.remove(child_path)
        file_map.pop(child_path, None)
        merged_count += 1

    print(f"  related_to resolved: {merged_count} recipe(s) merged.\n")


def _merge_name_parts(output_dir: str) -> None:
    """
    Merge recipes whose names contain explicit part indicators
    ("Part 1", "Part 2", "continued", etc.) into a single recipe.

    Uses recipe_merger.detect_recipe_part to identify candidates.
    """
    print("--- Post-processing: merging named parts ---")
    parsed_dir = Path(output_dir)
    groups: dict[str, list[tuple[Path, dict, str | None]]] = {}

    for f in parsed_dir.glob("*_parsed.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            continue

        base_name, part_indicator = detect_recipe_part(data.get("name", ""))
        norm_base = _normalize(base_name)
        if norm_base not in groups:
            groups[norm_base] = []
        groups[norm_base].append((f, data, part_indicator))

    merged_count = 0
    for norm_base, members in groups.items():
        # Only merge if at least one member has a part indicator
        if len(members) < 2:
            continue
        if not any(part for _, _, part in members):
            continue

        # Sort by part number, then filename
        def sort_key(item):
            _, _, part = item
            if not part:
                return (0, "")
            if part == "continued":
                return (999, "")
            if part.startswith("part_"):
                try:
                    return (int(part.split("_")[1]), "")
                except (IndexError, ValueError):
                    pass
            return (500, "")

        members.sort(key=sort_key)
        recipe_list = [data for _, data, _ in members]
        merged = merge_recipe_parts(recipe_list)

        # Save merged into the first file, delete the rest
        first_path = members[0][0]
        with open(first_path, "w", encoding="utf-8") as fp:
            json.dump(merged, fp, indent=2, ensure_ascii=False)

        for path, _, _ in members[1:]:
            os.remove(path)

        names = [data.get("name") for _, data, _ in members]
        print(f"  Merged parts: {names} → '{merged.get('name')}'")
        merged_count += 1

    print(f"  Named parts merged: {merged_count} group(s).\n")


def ingest_docx(input_dir: str, output_dir: str = "data/parsed", model: str = CHAT_MODEL, skip_duplicates: bool = True) -> None:
    """
    Process all DOCX recipe files in a folder.
    Each document may contain multiple recipes, which will be saved as separate files.
    
    Args:
        input_dir: Directory containing DOCX files
        output_dir: Directory to save parsed recipes
        model: LLM model to use for parsing (default: configured CHAT_MODEL)
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
                # Inject metadata
                recipe["source_metadata"] = {
                    "filename": docx_file.name,
                    "path": str(docx_file),
                    "type": "docx"
                }

                recipe_name = recipe.get("name") or "unknown_recipe"
                
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


def ingest_excel(input_dir: str, output_dir: str = "data/parsed", model: str = CHAT_MODEL, skip_duplicates: bool = True) -> None:
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
                    # Inject metadata
                    recipe["source_metadata"] = {
                        "filename": xlsx_file.name,
                        "path": str(xlsx_file),
                        "type": "excel",
                        "sheet": sheet_name
                    }

                    recipe_name = recipe.get("name") or "unknown_recipe"
                    
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



if __name__ == "__main__":
    print("Starting Full Ingestion Pipeline...")
    
    # Paths
    RAW_DIR = Path("data/raw")
    PARSED_DIR = Path("data/parsed")
    
    # 1. Images
    print("\n--- Ingesting Images ---")
    ingest_images(str(RAW_DIR / "jpg_recipes"), str(PARSED_DIR / "images"))
    
    # 2. DOCX
    print("\n--- Ingesting DOCX ---")
    ingest_docx(str(RAW_DIR / "docx_recipes"), str(PARSED_DIR / "docx"))
    
    # 3. Excel
    print("\n--- Ingesting Excel ---")
    ingest_excel(str(RAW_DIR / "excel_recipes"), str(PARSED_DIR / "excel"))
    
    print("\nIngestion Complete.")
