# cli/main.py
import argparse
from pathlib import Path

from src.ingest import ingest_images, ingest_docx, ingest_excel
from src.index import build_index
from src.query import answer_question
from src.merge_recipes import merge_recipes

DATA_RAW = Path("data/raw")
DATA_PARSED = Path("data/parsed")
DATA_INDEX = Path("data/index")

def main():
    parser = argparse.ArgumentParser("recipe-rag")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest-images")
    sub.add_parser("ingest-docx")
    sub.add_parser("ingest-excel")
    sub.add_parser("build-index")
    sub.add_parser("merge-recipes")

    ask_p = sub.add_parser("ask")
    ask_p.add_argument("question", type=str)

    args = parser.parse_args()

    if args.cmd == "ingest-images":
        ingest_images(DATA_RAW / "jpg_recipes", DATA_PARSED)
    elif args.cmd == "ingest-docx":
        ingest_docx(DATA_RAW / "docx_recipes", DATA_PARSED)
    elif args.cmd == "ingest-excel":
        ingest_excel(DATA_RAW / "excel_recipes", DATA_PARSED)
    elif args.cmd == "build-index":
        build_index(str(DATA_PARSED), str(DATA_INDEX))
    elif args.cmd == "merge-recipes":
        merge_recipes(str(DATA_PARSED))
    elif args.cmd == "ask":
        ans = answer_question(args.question, str(DATA_INDEX))
        print(ans)

if __name__ == "__main__":
    main()

