from pathlib import Path
import json
import numpy as np
import faiss
import sys
import pickle
from rank_bm25 import BM25Okapi

from src.config import get_embedding_client, EMBEDDING_MODEL


# ---------- recipe → document ----------

def recipe_to_document(recipe: dict, recipe_id: str) -> dict:
    """Turn JSON of recipe into a text document for embeddings."""
    name = recipe.get("name", "Unknown recipe")
    ingredients = recipe.get("ingredients", [])
    steps = recipe.get("steps", [])
    other = recipe.get("other_details", {})
    classifications = recipe.get("classifications", {})

    ingredients_text = "\n".join(f"- {ing}" for ing in ingredients)
    steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
    other_text = "\n".join(f"{k}: {v}" for k, v in other.items())
    
    # Format classification text
    class_text = ""
    if classifications:
        class_text = "Classifications:\n"
        for k, v in classifications.items():
            if isinstance(v, list):
                v = ", ".join(v)
            class_text += f"- {k.replace('_', ' ').title()}: {v}\n"

    text = f"""Recipe ID: {recipe_id}
Name: {name}

Ingredients:
{ingredients_text}

Steps:
{steps_text}

Other details:
{other_text}

{class_text}
"""

    return {
        "id": recipe_id,
        "name": name,
        "text": text,
        "raw": recipe,  # keeping original JSON attached
    }


# ---------- loading recipes from a folder ----------

def load_recipes_from_dir(dir_path: str):
    """
    Load recipes from a directory of JSON files.

    Handles:
    - a single recipe dict
    - a dict with "recipes": [ ... ]
    - a top-level list of recipe dicts
    """
    recipes = []
    for path in Path(dir_path).rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Skipping {path} – JSON parse error: {e}")
            continue

        # Case 1: file is a single recipe dict
        if isinstance(data, dict):
            # maybe it has a "recipes" list inside
            if "recipes" in data and isinstance(data["recipes"], list):
                for i, rec in enumerate(data["recipes"]):
                    if not isinstance(rec, dict):
                        continue
                    recipe_id = f"{path.stem}_{i}"
                    recipes.append(recipe_to_document(rec, recipe_id))
            else:
                recipe_id = path.stem
                recipes.append(recipe_to_document(data, recipe_id))

        # Case 2: file is a list of recipes
        elif isinstance(data, list):
            for i, rec in enumerate(data):
                if not isinstance(rec, dict):
                    continue
                recipe_id = f"{path.stem}_{i}"
                recipes.append(recipe_to_document(rec, recipe_id))

        # Anything else: skip
        else:
            print(f"Skipping {path} – unsupported JSON structure: {type(data)}")

    print(f"Loaded {len(recipes)} recipes from {dir_path}")
    return recipes


# ---------- embedding helpers ----------

MAX_CHARS_PER_DOC = 6000      # truncate very long docs before embedding
BATCH_SIZE = 32               # number of docs per embedding call


def _truncate_for_embedding(text: str, max_chars: int = MAX_CHARS_PER_DOC) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for embedding]"


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype="float32")
    if vectors.size == 0:
        return vectors
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10
    return vectors / norms


def get_embeddings(texts):
    """Call OpenAI embeddings in batches, truncating long docs."""
    client = get_embedding_client()
    all_vectors = []

    if not texts:
        raise ValueError("No texts provided to get_embeddings()")

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch = [_truncate_for_embedding(t) for t in batch]

        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        all_vectors.extend([d.embedding for d in resp.data])

    arr = np.array(all_vectors, dtype="float32")
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


# ---------- index building ----------

def build_index(parsed_dir: str, index_dir: str) -> None:
    """
    Build the FAISS index from all parsed recipes and save it to disk.
    """
    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    docs = load_recipes_from_dir(parsed_dir)
    if not docs:
        raise ValueError(f"No recipes found in {parsed_dir}")

    texts = [d["text"] for d in docs]

    embeddings = get_embeddings(texts)
    embeddings = l2_normalize(embeddings).astype("float32")

    dim = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(embeddings)

    # save index
    faiss.write_index(faiss_index, str(index_path / "faiss.index"))

    # save docs metadata
    with open(index_path / "docs.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    # --- BM25 Indexing ---
    print("Building BM25 index...")
    tokenized_corpus = [doc["text"].lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    
    with open(index_path / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)
    # ---------------------

    print(f"Indexed {len(docs)} recipes into {index_dir} (FAISS + BM25).")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -m src.index <input_dir> <output_dir>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    build_index(input_dir, output_dir)
