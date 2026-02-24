# cli/main.py
import argparse
from pathlib import Path
import sys

# Ensure the root of the project is in the PYTHONPATH so we can import 'src'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest import ingest_images, ingest_docx, ingest_excel
from src.index import build_index
from src.query import answer_question
from src.menu_builder import generate_menu

DATA_RAW = Path("data/raw")
DATA_PARSED = Path("data/parsed")
DATA_INDEX = Path("data/indices")

def main():
    parser = argparse.ArgumentParser("recipe-rag")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest-images")
    sub.add_parser("ingest-docx")
    sub.add_parser("ingest-excel")
    build_p = sub.add_parser("build-index")
    build_p.add_argument("--source", type=str, default=str(DATA_PARSED), help="Source directory for recipes")

    ask_p = sub.add_parser("ask")
    ask_p.add_argument("question", type=str)

    menu_p = sub.add_parser("menu")
    menu_p.add_argument("query", type=str, help="Describe the type of menu you want")

    args = parser.parse_args()

    if args.cmd == "ingest-images":
        ingest_images(DATA_RAW / "jpg_recipes", DATA_PARSED / "images")
    elif args.cmd == "ingest-docx":
        ingest_docx(DATA_RAW / "docx_recipes", DATA_PARSED / "docx")
    elif args.cmd == "ingest-excel":
        ingest_excel(DATA_RAW / "excel_recipes", DATA_PARSED / "excel")
    elif args.cmd == "build-index":
        build_index(args.source, str(DATA_INDEX))
    elif args.cmd == "ask":
        ans = answer_question(args.question, str(DATA_INDEX))
        print(ans)
    elif args.cmd == "menu":
        ans = generate_menu(
            args.query,
            recipe_index_dir=str(DATA_INDEX),
            menu_index_dir="data/indices_menus",
            style_guide_path="data/chef_style_guide.md"
        )
        print("\n=== MENU CONCEPTS ===\n")
        
        # Check if ans is a string (error) or a stream
        if isinstance(ans, str):
            print(ans)
        else:
            for chunk in ans:
                print(chunk.text, end="", flush=True)
            print()

if __name__ == "__main__":
    main()

