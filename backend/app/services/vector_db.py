# backend/app/services/vector_db.py
import chromadb
from app.core.config import CHROMA_PATH, COLLECTION_NAME

class VectorDBService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

    def reset_collection(self):
        try:
            self.client.delete_collection(name=COLLECTION_NAME)
        except:
            pass
        self.collection = self.client.create_collection(name=COLLECTION_NAME)

    def add_batch(self, documents, metadatas, ids, embeddings):
        """Adds a processed batch to ChromaDB."""
        if not documents:
            return
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

    def search(self, query_embedding, k=15):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas"]
        )
    
    def count(self):
        try:
            # Refresh collection reference in case it was deleted/recreated
            self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
            return self.collection.count()
        except Exception as e:
            print(f"⚠️ Could not get count: {e}")
            return 0

    def get_example_queries(self):
        try:
            # Check if collection exists and has data
            self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
            if self.collection.count() == 0:
                return []
            
            results = self.collection.get(limit=10, include=["metadatas"])
            # ... rest of your logic ...
            examples = []
            seen = set()
            for meta in results.get('metadatas', []):
                h = meta.get('header')
                s = meta.get('sheet')
                if h and (h, s) not in seen:
                    examples.append(f"What is the {h} in {s}?")
                    seen.add((h, s))
            return examples[:5]
        except Exception as e:
            print(f"⚠️ Could not get examples: {e}")
            return []

vector_db = VectorDBService()