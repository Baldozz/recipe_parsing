from src.ingest import ingest_docx, ingest_excel
from pathlib import Path

if __name__ == "__main__":
    print("🚀 Starting Dedicated Document Ingestion...")
    
    RAW_DIR = Path("data/raw")
    PARSED_DIR = Path("data/parsed")
    
    # Run these in parallel to the main ingestion (they target different output folders)
    print("\n--- Ingesting DOCX ---")
    try:
        ingest_docx(str(RAW_DIR / "docx_recipes"), str(PARSED_DIR / "docx"))
    except Exception as e:
        print(f"DOCX Failed: {e}")
        
    print("\n--- Ingesting Excel ---")
    try:
        ingest_excel(str(RAW_DIR / "excel_recipes"), str(PARSED_DIR / "excel"))
    except Exception as e:
        print(f"Excel Failed: {e}")
        
    print("\nDocument Ingestion Complete.")
