#!/bin/bash
set -e

echo "============================================"
echo "Starting Pipeline Part 2 (Post-Review)"
echo "============================================"

# 2. Stitching
echo "[1/4] Stitching Multi-Part Recipes..."
python3 src/stitch_recipes.py

# 3. Extraction
echo "[2/4] Extracting English Recipes..."
python3 src/extract_english.py

# 4. Deduplication
echo "[3/4] Deduplicating Recipes..."
python3 src/find_duplicates.py --dir data/english_recipes --archive data/archived_duplicates --fix

# 5. Enrichment
echo "[4/4] Enriching Recipes (LLM)..."
PYTHONPATH=. python3 cli/main.py enrich --source data/english_recipes --dest data/enriched_recipes

echo "============================================"
echo "Pipeline Complete!"
echo "============================================"
