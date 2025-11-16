from pathlib import Path
import os
import json

from .parsers.jpeg_parser import parse_recipe_image
from .parsers.docx_parser import parse_recipe_docx
from .parsers.excel_parser import parse_excel_file


def ingest_images(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o") -> None:
    """
    Process all recipe images in a folder (ported from your batch_process_recipes).
    """
    os.makedirs(output_dir, exist_ok=True)

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    input_path = Path(input_dir)
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"No image files found in {input_dir}")
        return

    print(f"Found {len(image_files)} recipe images\n")

    results = []

    for i, image_file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Processing: {image_file.name}")

        try:
            recipe = parse_recipe_image(str(image_file), model=model)

            output_filename = image_file.stem + "_parsed.json"
            output_path = Path(output_dir) / output_filename

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(recipe, indent=2, fp=f, ensure_ascii=False)

            results.append(
                {
                    "source_file": image_file.name,
                    "output_file": output_filename,
                    "status": "success",
                    "recipe_name": recipe.get("name", "Unknown"),
                }
            )

            print(f"Success: {recipe.get('name', 'Unknown')}\n")

        except Exception as e:
            print(f"Error: {e}\n")
            results.append(
                {
                    "source_file": image_file.name,
                    "status": "error",
                    "error": str(e),
                }
            )

    summary_path = Path(output_dir) / "_processing_summary_images.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"Image processing complete: {successful}/{len(results)} successful")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


def ingest_docx(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o") -> None:
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(input_dir)
    docx_files = [f for f in input_path.iterdir() if f.suffix.lower() == ".docx"]

    if not docx_files:
        print(f"No .docx files found in {input_dir}")
        return

    print(f"Found {len(docx_files)} DOCX recipe files\n")

    results = []

    for i, docx_file in enumerate(docx_files, 1):
        print(f"[{i}/{len(docx_files)}] Processing: {docx_file.name}")
        try:
            recipe = parse_recipe_docx(str(docx_file), model=model)

            output_filename = docx_file.stem + "_parsed.json"
            output_path = Path(output_dir) / output_filename

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(recipe, indent=2, fp=f, ensure_ascii=False)

            results.append(
                {
                    "source_file": docx_file.name,
                    "output_file": output_filename,
                    "status": "success",
                    "recipe_name": recipe.get("name", "Unknown"),
                }
            )

            print(f"Success: {recipe.get('name', 'Unknown')}\n")

        except Exception as e:
            print(f"Error: {e}\n")
            results.append(
                {
                    "source_file": docx_file.name,
                    "status": "error",
                    "error": str(e),
                }
            )

    summary_path = Path(output_dir) / "_processing_summary_docx.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"DOCX processing complete: {successful}/{len(results)} successful")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)


def ingest_excel(input_dir: str, output_dir: str = "data/parsed", model: str = "gpt-4o") -> None:
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(input_dir)
    xlsx_files = [f for f in input_path.iterdir() if f.suffix.lower() in {".xlsx", ".xls"}]

    if not xlsx_files:
        print(f"No Excel files found in {input_dir}")
        return

    print(f"Found {len(xlsx_files)} Excel files\n")

    results = []

    for i, xlsx_file in enumerate(xlsx_files, 1):
        print(f"[{i}/{len(xlsx_files)}] Processing: {xlsx_file.name}")
        try:
            for sheet_idx, (sheet_name, recipe) in enumerate(parse_excel_file(str(xlsx_file), model=model)):
                base_name = f"{xlsx_file.stem}_{sheet_name}_{sheet_idx}_parsed"
                output_filename = base_name + ".json"
                output_path = Path(output_dir) / output_filename

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(recipe, indent=2, fp=f, ensure_ascii=False)

                results.append(
                    {
                        "source_file": xlsx_file.name,
                        "sheet": sheet_name,
                        "output_file": output_filename,
                        "status": "success",
                        "recipe_name": recipe.get("name", "Unknown"),
                    }
                )

                print(f"    Success: {recipe.get('name', 'Unknown')}")

            print()

        except Exception as e:
            print(f"Error in {xlsx_file.name}: {e}\n")
            results.append(
                {
                    "source_file": xlsx_file.name,
                    "status": "error",
                    "error": str(e),
                }
            )

    summary_path = Path(output_dir) / "_processing_summary_excel.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, indent=2, fp=f, ensure_ascii=False)

    successful = sum(1 for r in results if r["status"] == "success")
    print("=" * 50)
    print(f"Excel processing complete: {successful}/{len(results)} successful")
    print(f"Results saved to: {output_dir}")
    print("=" * 50)
