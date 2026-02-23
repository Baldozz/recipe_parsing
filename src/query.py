import os
import time
from pathlib import Path
import json
import numpy as np
import faiss
import pickle
import google.generativeai as genai
from rank_bm25 import BM25Okapi

from src.config import get_chat_client, CHAT_MODEL
from src.index import l2_normalize, get_embeddings  # reuse
from src.utils.retry import call_model_with_retry


def load_index(index_dir: str):
    """
    Load a precomputed FAISS index, BM25 index, and docs metadata from disk.
    """
    index_path = Path(index_dir)
    faiss_index = faiss.read_index(str(index_path / "faiss.index"))
    
    with open(index_path / "docs.json", "r", encoding="utf-8") as f:
        docs = json.load(f)
        
    bm25 = None
    if (index_path / "bm25.pkl").exists():
        with open(index_path / "bm25.pkl", "rb") as f:
            bm25 = pickle.load(f)
            
    return faiss_index, bm25, docs


def retrieve(docs, faiss_index, bm25, query: str, k: int = 20, filters: dict = None):
    """
    Hybrid Search: FAISS (Vector) + BM25 (Keyword).
    Combines results using Reciprocal Rank Fusion (RRF).
    Supports post-filtering by metadata.
    """
    # --- 1. Vector Search (FAISS) ---
    q_emb = get_embeddings([query])
    q_emb = l2_normalize(q_emb).astype("float32")
    
    # Fetch more candidates for RRF and filtering
    search_k = k * 20 if filters else k * 5
    
    v_scores, v_ids = faiss_index.search(q_emb, search_k)
    v_scores = v_scores[0]
    v_ids = v_ids[0]
    
    # --- 2. Keyword Search (BM25) ---
    bm25_results = []
    if bm25:
        tokenized_query = query.lower().split()
        # Get top N docs from BM25
        # bm25.get_top_n returns the actual docs, but we need indices.
        # So we use get_scores and sort.
        doc_scores = bm25.get_scores(tokenized_query)
        # Get top search_k indices
        bm25_indices = np.argsort(doc_scores)[::-1][:search_k]
        bm25_results = [(idx, doc_scores[idx]) for idx in bm25_indices]
    
    # --- 3. Reciprocal Rank Fusion (RRF) ---
    # RRF score = 1 / (k + rank)
    rrf_k = 60
    doc_scores_map = {} # doc_idx -> score
    
    # Process Vector Results
    for rank, idx in enumerate(v_ids):
        if idx == -1: continue
        if idx not in doc_scores_map: doc_scores_map[idx] = 0.0
        doc_scores_map[idx] += 1 / (rrf_k + rank + 1)
        
    # Process BM25 Results
    for rank, (idx, score) in enumerate(bm25_results):
        if idx not in doc_scores_map: doc_scores_map[idx] = 0.0
        doc_scores_map[idx] += 1 / (rrf_k + rank + 1)
    
    # Sort by RRF score
    sorted_docs = sorted(doc_scores_map.items(), key=lambda item: item[1], reverse=True)
    
    # --- 4. Filtering & Formatting ---
    results = []
    for idx, rrf_score in sorted_docs:
        doc = docs[idx]
        
        # Post-Filtering Logic
        if filters:
            match = True
            doc_meta = doc.get("raw", {}).get("classifications", {})
            for key, required_val in filters.items():
                doc_val = doc_meta.get(key)
                if not doc_val:
                    # If metadata is missing, we give benefit of the doubt and INCLUDE it.
                    # Rely on semantic/keyword search to be correct.
                    continue
                if isinstance(doc_val, list):
                    if required_val not in doc_val:
                        match = False
                        break
                else:
                    if required_val.lower() not in doc_val.lower():
                        match = False
                        break
            if not match:
                continue
        
        results.append({"doc": doc, "score": float(rrf_score)})
        if len(results) >= k:
            break
            
    return results


# ------- prompt-size-safe answer function -------

MAX_CHARS_PER_DOC = 8000
MAX_TOTAL_CHARS = 200000

def _truncate_for_prompt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"

# Configure GenAI
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def answer_question(
    query: str,
    index_dir: str,
    model: str = "gemini-2.0-flash", # Default to Flash for RAG
    k: int = 20,
    filters: dict = None,
) -> str:
    """
    Answer a question using the indexed recipes using Gemini.
    """
    faiss_index, bm25, docs = load_index(index_dir)
    retrieved = retrieve(docs, faiss_index, bm25, query, k=k, filters=filters)
    if not retrieved:
        return "I couldn't find any relevant recipes for that question."

    context_blocks = []
    total_len = 0

    for r in retrieved:
        d = r["doc"]
        block = f"### Recipe: {d['name']} (ID: {d['id']})\n{d['text']}"

        # truncate a single recipe if it's huge
        block = _truncate_for_prompt(block, MAX_CHARS_PER_DOC)

        # enforce total context limit
        if total_len + len(block) > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total_len
            if remaining <= 0:
                break
            block = block[:remaining] + "\n...[truncated]"
        context_blocks.append(block)
        total_len += len(block)

    context_text = "\n\n".join(context_blocks)

    # Use Gemini
    genai_model = genai.GenerativeModel(model)

    prompt = f"""
    You are a helpful cooking assistant. Answer user questions using ONLY the provided recipes.
    If the answer is not clearly supported by the recipes, say that you are not sure.
    
    User question:
    {query}
    
    Here are some potentially relevant recipes from the database:
    {context_text}
    """

    try:
        response = call_model_with_retry(genai_model, prompt)
        return response.text
    except Exception as e:
        return f"Error answering question: {e}"
