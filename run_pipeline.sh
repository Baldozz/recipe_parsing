#!/bin/bash
set -e  # Exit on error

echo "============================================"
echo "Starting Recipe Processing Pipeline"
echo "THREE-PHASE ARCHITECTURE"
echo "============================================"

# Phase 1: Extract with recipe_type classification
echo "[1/6] Parsing Images (Phase 1: Extraction)..."
PYTHONPATH=. python3 cli/main.py ingest-images

echo "[2/6] Parsing DOCX..."
PYTHONPATH=. python3 cli/main.py ingest-docx

echo "[3/6] Parsing Excel..."
PYTHONPATH=. python3 cli/main.py ingest-excel

# Phase 2: Merge continuations based on is_continuation_of flag
echo "[4/6] Merging Recipe Continuations (Phase 2)..."
python3 src/merge_continuations.py data/parsed data/stitched

# Phase 3: Detect global component links
echo "[5/6] Detecting Component Links (Phase 3)..."
python3 src/link_recipes.py data/stitched data/linked

# Extract English recipes from linked data
echo "[6/6] Extracting English Recipes..."
python3 src/extract_english.py

echo "============================================"
echo "Three-Phase Pipeline Complete!"
echo " - Phase 1: Extracted recipes with recipe_type"
echo " - Phase 2: Stitched continuations & merged assembly"
echo " - Phase 3: Built component dependency graph"
echo ""
echo "Next: Run 'python3 src/review_titles.py' to review titles."
echo "Then: './run_pipeline_part2.sh' for deduplication & enrichment."
echo "============================================"

