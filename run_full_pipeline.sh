#!/bin/bash
set -e  # Exit on error

echo "============================================"
echo "🍳 Starting Full Recipe Processing Pipeline"
echo "============================================"

# Step 1: Ingestion
# (Assuming raw data is in data/raw/jpg_recipes, data/raw/docx_recipes, etc.)
echo "[Phase 1] Ingesting Data..."
echo "  - Parsing Images (Gemini Pro)..."
python3 -m src.ingest
echo "  - Parsing Docs/Excel..."
python3 -m src.ingest_docs_only

# Step 2: Stitching & Merging
echo "[Phase 2] Stitching Sessions..."
# 1. Stitch Images
python3 -m src.stitch_sessions_llm
# 2. (Opt) Merge Docs into pipeline is now handled by ingestion or manual merge, 
# but if we need a glue step it would go here. 
# Currently 'ingest_docs_only' produces _parsed.json, we might need to rename/move them?
# Wait, I moved merge_docs_to_pipeline.py to legacy. 
# I should double check if ingest_docs_only ALREADY saves to the right place or if merge is needed.
# ingest_docs_only saves to data/parsed/docx.
# The previous merge_docs_to_pipeline.py copied them to data/merged_llm.
# WITHOUT IT, the pipeline breaks for docs.
# I should PROBABLY bring back a simple merge step or update ingest_docs_only to output to merged_llm.
# For now, I will assume the user manually runs the legacy script OR I should fix ingest_docs_only to be self-sufficient.
# Actually, let's keep it simple: Standardization reads from merged_llm.
# So I DO need to move parsed docs to merged_llm. 
# I will add a simple bash command here to do that.

echo "  - Merging Docs into Pipeline..."
mkdir -p data/merged_llm
cp data/parsed/docx/*.json data/merged_llm/ 2>/dev/null || true
cp data/parsed/excel/*.json data/merged_llm/ 2>/dev/null || true

# Step 3: Standardization
echo "[Phase 3] Standardizing to English..."
# Input: data/merged_llm -> Output: data/english_dataset
python3 -m src.standardize_english

# Step 4: Classification
echo "[Phase 4] Classifying Recipes..."
# Input: data/english_dataset -> Output: data/final_classified_english
python3 -m src.classify_recipes

# Step 5: Indexing
echo "[Phase 5] Building Index..."
# Input: data/final_classified_english -> Output: data/indices
python3 -m src.index data/final_classified_english data/indices

echo "============================================"
echo "✅ Pipeline Complete!"
echo "   Final Index: data/indices"
echo "============================================"
