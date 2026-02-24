from pathlib import Path
import json
import numpy as np
import faiss
import sys
import pickle
from rank_bm25 import BM25Okapi
import google.generativeai as genai
import time
from dotenv import load_dotenv

load_dotenv()

def menu_to_document(menu_data: dict, menu_id: str) -> dict:
    filename = menu_data.get("filename", "Unknown")
    date = menu_data.get("event_date", "Unknown")
    event_name = menu_data.get("event_name", "Unknown")
    
    text = f"Menu ID: {menu_id}\nEvent: {event_name}\nDate: {date}\nFilename: {filename}\n\nCourses:\n"
    
    for course in menu_data.get("courses", []):
        course_name = course.get("course_name", "Course")
        text += f"[{course_name}]\n"
        for dish in course.get("dishes", []):
            dish_name = dish.get("dish_name", "")
            desc = dish.get("description", "")
            if desc:
                text += f"  - {dish_name}: {desc}\n"
            else:
                text += f"  - {dish_name}\n"
        text += "\n"
        
    return {
        "id": menu_id,
        "name": f"{event_name} ({date})",
        "text": text,
        "raw": menu_data,
    }

def load_menus_from_dir(dir_path: str):
    docs = []
    for path in Path(dir_path).rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                docs.append(menu_to_document(data, path.stem))
        except Exception as e:
            print(f"Skipping {path} - Error: {e}")
    print(f"Loaded {len(docs)} menus from {dir_path}")
    return docs

def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype="float32")
    if vectors.size == 0:
        return vectors
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10
    return vectors / norms

def get_embeddings(texts):
    import os
    if "GEMINI_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    BATCH_SIZE = 32
    all_vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        
        retries = 3
        for attempt in range(retries):
            try:
                resp = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=batch,
                    task_type="retrieval_document"
                )
                all_vectors.extend(resp['embedding'])
                break
            except Exception as e:
                print(f"Embedding failed, attempt {attempt+1}: {e}")
                time.sleep(2 * (attempt + 1))
                if attempt == retries - 1:
                    raise e
                    
    arr = np.array(all_vectors, dtype="float32")
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr

def build_index(parsed_dir: str, index_dir: str):
    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    docs = load_menus_from_dir(parsed_dir)
    if not docs:
        raise ValueError(f"No menus found in {parsed_dir}")

    texts = [d["text"] for d in docs]

    print("Fetching embeddings...")
    embeddings = get_embeddings(texts)
    embeddings = l2_normalize(embeddings).astype("float32")

    dim = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(embeddings)

    faiss.write_index(faiss_index, str(index_path / "faiss.index"))

    with open(index_path / "docs.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print("Building BM25 index...")
    tokenized_corpus = [doc["text"].lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    
    with open(index_path / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)

    print(f"Indexed {len(docs)} menus into {index_dir} (FAISS + BM25).")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 src/index_menus.py <input_dir> <output_dir>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    build_index(input_dir, output_dir)
