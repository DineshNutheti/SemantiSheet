# backend/app/services/embedding.py
from typing import List
from sentence_transformers import SentenceTransformer
import torch
from app.core.config import EMBEDDING_MODEL_NAME

class LocalEmbeddingService:
    def __init__(self):
        # Auto-detect GPU (CUDA/MPS) or fallback to CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu" and torch.backends.mps.is_available():
            device = "mps" # For Mac M1/M2/M3
            
        print(f"🧠 Loading Local Embedding Model: {EMBEDDING_MODEL_NAME} on {device}...")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of texts locally.
        Much faster than API calls for large datasets.
        """
        if not texts:
            return []
            
        # normalize_embeddings=True improves retrieval quality for dot-product/cosine
        embeddings = self.model.encode(
            texts, 
            batch_size=32, 
            show_progress_bar=False, 
            normalize_embeddings=True
        )
        # Convert numpy array to list of lists
        return embeddings.tolist()

# Singleton instance
embedding_service = LocalEmbeddingService()