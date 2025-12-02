#!/bin/bash
set -e  # Exit on error

echo "============================================"
echo "Starting Recipe Processing Pipeline"
echo "============================================"

# 1. Ingestion (Resumable)
echo "[1/5] Ingesting Images..."
PYTHONPATH=. python3 cli/main.py ingest-images

echo "[2/5] Ingesting DOCX..."
PYTHONPATH=. python3 cli/main.py ingest-docx

echo "[3/5] Ingesting Excel..."
PYTHONPATH=. python3 cli/main.py ingest-excel

# 2. Stitching
echo "[4/5] Stitching Multi-Part Recipes..."
# Note: Stitching runs on the initial parsed data before extraction
python3 src/stitch_recipes.py

# 3. Extraction
echo "[5/5] Extracting English Recipes..."
python3 src/extract_english.py

# 4. Deduplication
echo "[6/5] Deduplicating Recipes..."
python3 src/find_duplicates.py --dir data/english_recipes --archive data/archived_duplicates --fix

# 5. Enrichment
echo "[7/5] Enriching Recipes (LLM)..."
# Clear destination first to ensure clean run? Or keep it resumable?
# The user wanted a "clean run" earlier, but enrich is resumable.
# If we want to force re-enrichment of everything, we should clear it.
# But since we just cleared it in a previous step (before ingestion started), 
# and ingestion is just adding files, we can just run enrich.
PYTHONPATH=. python3 cli/main.py enrich --source data/english_recipes --dest data/enriched_recipes

echo "============================================"
echo "Pipeline Complete!"
echo "============================================"
