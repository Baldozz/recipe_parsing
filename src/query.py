from pathlib import Path
import json
import numpy as np
import faiss

from src.config import get_chat_client, CHAT_MODEL
from src.index import l2_normalize, get_embeddings  # reuse


def load_index(index_dir: str):
    """
    Load a precomputed FAISS index and its docs metadata from disk.
    """
    index_path = Path(index_dir)
    faiss_index = faiss.read_index(str(index_path / "faiss.index"))
    with open(index_path / "docs.json", "r", encoding="utf-8") as f:
        docs = json.load(f)
    return faiss_index, docs


def retrieve(docs, faiss_index, query: str, k: int = 20):
    """
    Embed ONLY the query, then search the FAISS index.
    """
    # embed query (this is very small, no token issues here)
    q_emb = get_embeddings([query])
    q_emb = l2_normalize(q_emb).astype("float32")

    scores, ids = faiss_index.search(q_emb, k)
    scores = scores[0]
    ids = ids[0]

    results = []
    for score, idx in zip(scores, ids):
        if idx == -1:
            continue
        doc = docs[idx]
        results.append({"doc": doc, "score": float(score)})
    return results


# ------- prompt-size-safe answer function -------

MAX_CHARS_PER_DOC = 8000 
MAX_TOTAL_CHARS = 200000   


def _truncate_for_prompt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


def answer_question(
    query: str,
    index_dir: str,
    model: str | None = None,
    k: int = 20,
) -> str:
    """
    Answer a question using the indexed recipes, while keeping the prompt
    under the model's context limit by truncating docs and enforcing a
    total character budget.
    """
    faiss_index, docs = load_index(index_dir)
    retrieved = retrieve(docs, faiss_index, query, k=k)
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

    client = get_chat_client()
    model = model or CHAT_MODEL

    system_msg = """
You are a helpful cooking assistant. Answer user questions using ONLY the provided recipes.
If the answer is not clearly supported by the recipes, say that you are not sure.
"""

    user_msg = f"""User question:
{query}

Here are some potentially relevant recipes from the database:

{context_text}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )

    return resp.choices[0].message.content
