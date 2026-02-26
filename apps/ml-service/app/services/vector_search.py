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

    def add_or_update(self, id: str, text: str, extra_meta: dict = None):
        """
        Upsert a single profile into the vector index.
        If the ID already exists, removes the old entry first.
        Note: FAISS IndexFlatIP doesn't support in-place deletion, so we
        rebuild the index without the stale entry when updating.
        """
        if id in self.metadata:
            # Remove the stale entry by rebuilding without it
            keep_positions = [i for i, m in enumerate(self.metadata) if m != id]
            if keep_positions:
                all_vectors = self.index.reconstruct_n(0, self.index.ntotal)
                kept_vectors = np.array([all_vectors[i] for i in keep_positions]).astype("float32")
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(kept_vectors)
                self.metadata = [self.metadata[i] for i in keep_positions]
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = []

        # Add the new/updated embedding
        embedding = self.model.encode([text])
        faiss.normalize_L2(embedding)
        self.index.add(np.array(embedding).astype("float32"))
        self.metadata.append(id)
        logger.info(f"Upserted user {id} into vector index (total: {len(self.metadata)})")

    def persist_index(self, path: str = "registry/vector_index.faiss"):
        """Convenience alias for save_index — called after each live upsert."""
        self.save_index(path)

