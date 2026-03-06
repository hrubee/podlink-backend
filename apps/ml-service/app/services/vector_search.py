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
        # Wrap with IndexIDMap to support ID-based operations like remove_ids in O(1) lookup
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
        self.metadata = {}  # { int_id: ext_str_id }
        self._next_id = 1

    def _get_or_create_internal_id(self, ext_id: str) -> int:
        for int_id, eid in self.metadata.items():
            if eid == ext_id:
                return int_id
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def add_texts(self, ids: List[str], texts: List[str]):
        """Generates embeddings and adds them to the FAISS index."""
        if not texts:
            return
            
        embeddings = self.model.encode(texts)
        faiss.normalize_L2(embeddings)
        
        int_ids = []
        new_metadata = dict(self.metadata)
        for ext_id in ids:
            int_id = self._get_or_create_internal_id(ext_id)
            int_ids.append(int_id)
            new_metadata[int_id] = ext_id
            
        self.index.add_with_ids(np.array(embeddings).astype('float32'), np.array(int_ids).astype('int64'))
        self.metadata = new_metadata
        logger.info(f"Added {len(texts)} items to vector index.")

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Performs semantic search."""
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.index.search(np.array(query_embedding).astype('float32'), top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx in self.metadata:
                results.append({
                    "id": self.metadata[idx],
                    "score": float(dist)
                })
        return results

    def save_index(self, path: str = "registry/vector_index.faiss"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Atomic rename implementation for saving
        temp_path = f"{path}.temp"
        faiss.write_index(self.index, temp_path)
        os.rename(temp_path, path)
        
        import json
        with open(f"{path}.metadata.temp", "w") as f:
            json.dump({"metadata": self.metadata, "next_id": self._next_id}, f)
        os.rename(f"{path}.metadata.temp", f"{path}.metadata")

    def load_index(self, path: str = "registry/vector_index.faiss"):
        if os.path.exists(path):
            try:
                self.index = faiss.read_index(path)
                import json
                with open(f"{path}.metadata", "r") as f:
                    data = json.load(f)
                    
                # Support backwards compatibility with old list-style metadata
                if isinstance(data, list):
                    logger.warning("Migrating old list-style metadata to dict-style.")
                    self.metadata = {}
                    for i, ext_id in enumerate(data):
                        self.metadata[i] = ext_id
                    self._next_id = len(data)
                else:
                    self.metadata = {int(k): v for k, v in data.get("metadata", {}).items()}
                    self._next_id = data.get("next_id", max(self.metadata.keys(), default=0) + 1)
                logger.info("Loaded existing vector index.")
            except Exception as e:
                logger.warning(f"Failed loading index ({e}), starting fresh.")
                self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))

    def add_or_update(self, id: str, text: str, extra_meta: dict = None):
        """
        Upsert a single profile into the vector index cleanly using IDMap.
        """
        int_id = None
        for k, v in self.metadata.items():
            if v == id:
                int_id = k
                break
                
        if int_id is not None:
            # Remove the stale vectors by internal ID map cleanly
            self.index.remove_ids(np.array([int_id]).astype('int64'))
        else:
            int_id = self._next_id
            self._next_id += 1
            
        # Add the new/updated embedding
        embedding = self.model.encode([text])
        faiss.normalize_L2(embedding)
        
        new_metadata = dict(self.metadata)
        new_metadata[int_id] = id
        
        self.index.add_with_ids(np.array(embedding).astype("float32"), np.array([int_id]).astype("int64"))
        self.metadata = new_metadata
        
        logger.info(f"Upserted user {id} into vector index (total: {len(self.metadata)})")

    def persist_index(self, path: str = "registry/vector_index.faiss"):
        """Convenience alias for save_index — called after each live upsert."""
        self.save_index(path)

