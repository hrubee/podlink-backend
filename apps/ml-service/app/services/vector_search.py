import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

class VectorSearchService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatIP(self.dimension) # Inner Product for Cosine Similarity on normalized vectors
        self.metadata = [] # Stores mapping of index to external_id

    def add_texts(self, ids: List[str], texts: List[str]):
        """Generates embeddings and adds them to the FAISS index."""
        if not texts:
            return
            
        embeddings = self.model.encode(texts)
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        self.index.add(np.array(embeddings).astype('float32'))
        self.metadata.extend(ids)
        logger.info(f"Added {len(texts)} items to vector index.")

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Performs semantic search."""
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.index.search(np.array(query_embedding).astype('float32'), top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1: # FAISS returns -1 if not enough matches
                results.append({
                    "id": self.metadata[idx],
                    "score": float(dist)
                })
        return results

    def save_index(self, path: str = "registry/vector_index.faiss"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        faiss.write_index(self.index, path)
        # In a real system, we'd also save the metadata list to a JSON/Pickle file
        import json
        with open(f"{path}.metadata", "w") as f:
            json.dump(self.metadata, f)

    def load_index(self, path: str = "registry/vector_index.faiss"):
        if os.path.exists(path):
            self.index = faiss.read_index(path)
            import json
            with open(f"{path}.metadata", "r") as f:
                self.metadata = json.load(f)
            logger.info("Loaded existing vector index.")
