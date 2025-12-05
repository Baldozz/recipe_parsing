#!/bin/bash
set -e  # Exit on error

echo "============================================"
echo "Starting Full Recipe Processing Pipeline"
echo "============================================"

# Phase 1: Ingestion (Assumed running/done via cli/main.py)
# We skip calling ingestion here to avoid re-running it, but list it for clarity.
# PYTHONPATH=. python3 cli/main.py ingest-images
# PYTHONPATH=. python3 cli/main.py ingest-docx
# PYTHONPATH=. python3 cli/main.py ingest-excel

# Phase 2: Stitching (Merge Continuations)
# Phase 2: Stitching (Merge Continuations)
echo "[Phase 2] Stitching Recipes..."
python3 -m src.stitch_recipes recipe_parsing/data/parsed recipe_parsing/data/merged

# Phase 3: Linking (Global Component Detection)
echo "[Phase 3] Detecting Component Links..."
python3 recipe_parsing/src/link_recipes.py recipe_parsing/data/merged recipe_parsing/data/linked

# Phase 4: Extraction
echo "[Phase 4] Extracting English Recipes..."
# extract_english.py now uses rglob to find all json files in data/linked recursively
python3 recipe_parsing/src/extract_english.py

echo "============================================"
echo "Pipeline Complete!"
echo "============================================"
