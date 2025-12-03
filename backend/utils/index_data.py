# src/index_data.py
"""
Core indexer for semantic spreadsheet search.

This module:
  - Reads Excel files from a 'data' directory.
  - Uses SheetParser to convert rows to semantic text + metadata.
  - Generates embeddings with Gemini.
  - Stores everything in a ChromaDB collection.

The FastAPI backend imports and calls `index_spreadsheet_data()`.
You can also run this file directly: `python -m src.index_data` (from project root).
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

# Since this file is inside `src/`, use relative import to ingestion.py
from .ingestion import SheetParser, SpreadsheetRow


# --- CONFIGURATION ---

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "spreadsheet_concepts"
EMBEDDING_MODEL = "models/text-embedding-004"

genai.configure(api_key=API_KEY)
gemini_client = genai


def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for a single text string.
    (One call per row – simple and reliable.)
    """
    resp = gemini_client.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
    )
    return resp["embedding"]


def index_spreadsheet_data(data_dir: Optional[str] = None) -> int:
    """
    Parse all Excel files in `data_dir` (default: ./data),
    create embeddings, and index into ChromaDB.

    Returns:
        int: number of concepts indexed.
    """
    if data_dir is None:
        data_dir = os.path.join(os.getcwd(), "data")

    if not os.path.exists(data_dir):
        raise FileNotFoundError("'data' directory not found at: {}".format(data_dir))

    # Collect .xlsx / .xls files
    data_files = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().endswith((".xlsx", ".xls"))
    ]

    if not data_files:
        raise FileNotFoundError("No Excel files found in data directory: {}".format(data_dir))

    print("📂 Indexing the following Excel files:")
    for fp in data_files:
        print("  - {}".format(os.path.basename(fp)))

    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        # Ok if it doesn't exist yet
        pass

    collection = chroma_client.create_collection(name=COLLECTION_NAME)

    all_rows = []  # type: List[SpreadsheetRow]

    # 1. Parse data from all files
    for filepath in data_files:
        print("\n🔍 Parsing spreadsheet: {}".format(os.path.basename(filepath)))
        parser = SheetParser(filepath)
        try:
            parsed_rows = parser.parse()
        except Exception as e:
            print("   ❌ Error parsing {}: {}".format(os.path.basename(filepath), e))
            continue

        print("   ✅ Parsed {} rows from {}".format(len(parsed_rows), os.path.basename(filepath)))
        all_rows.extend(parsed_rows)

    if not all_rows:
        print("❌ No rows were successfully parsed from any spreadsheet.")
        return 0

    print("\n📊 Total rows ready for indexing: {}".format(len(all_rows)))

    # 2. Prepare documents & metadata
    documents = [row.semantic_text for row in all_rows]
    metadatas = [row.to_dict()["metadata"] for row in all_rows]
    ids = ["doc_{}".format(i) for i in range(len(all_rows))]

    # 3. Generate embeddings (simple loop – fine for our test size)
    embeddings = []  # type: List[List[float]]

    print("\n🧠 Generating embeddings via Gemini...")
    for i, doc in enumerate(documents):
        try:
            emb = get_embedding(doc)
            embeddings.append(emb)
        except Exception as e:
            print("   ❌ Embedding failed for row {}: {}".format(i, e))
            # we could skip or add a dummy vector; here we skip this row completely
            continue

    # Safety: ensure lengths match
    min_len = min(len(embeddings), len(documents), len(metadatas), len(ids))
    embeddings = embeddings[:min_len]
    documents = documents[:min_len]
    metadatas = metadatas[:min_len]
    ids = ids[:min_len]

    # 4. Add to ChromaDB
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    count = collection.count()
    print("\n✅ Indexing complete. Indexed {} total concepts in '{}'.".format(count, COLLECTION_NAME))
    return count


def main():
    try:
        n = index_spreadsheet_data()
        if n > 0:
            print("\n🎉 Finished indexing {} concepts.".format(n))
        else:
            print("\n⚠️ Indexing finished but no concepts were indexed.")
    except Exception as e:
        print("\n🔴 Indexing failed: {}".format(e))


if __name__ == "__main__":
    main()
