import torch
import numpy as np
from typing import List, Dict
from app.models.recommender import NCFModel

class RankingService:
    def __init__(self, model_path="registry/latest.pt"):
        # In production, we'd load num_users/num_items from a metadata store
        self.model = NCFModel(num_users=10000, num_items=10000)
        if torch.cuda.is_available():
            self.model.load_state_dict(torch.load(model_path))
            self.model.cuda()
        else:
            self.model.load_state_dict(torch.load(model_path, map_location='cpu'))
        self.model.eval()

    def get_recommendations(self, user_id: int, candidate_ids: List[int], top_k=10):
        """Ranks a list of candidate guests/podcasts for a specific user."""
        user_tensor = torch.tensor([user_id] * len(candidate_ids))
        item_tensor = torch.tensor(candidate_ids)
        
        if torch.cuda.is_available():
            user_tensor, item_tensor = user_tensor.cuda(), item_tensor.cuda()
            
        with torch.no_grad():
            scores = self.model(user_tensor, item_tensor).cpu().numpy().flatten()
            
        # Combine and sort
        ranked_indices = np.argsort(scores)[::-1]
        sorted_candidates = [candidate_ids[i] for i in ranked_indices]
        sorted_scores = [float(scores[i]) for i in ranked_indices]
        
        return sorted_candidates[:top_k], sorted_scores[:top_k]

    def cold_start_resolver(self, profile_embedding: np.ndarray, global_top_hits: List[int]):
        """
        Handles cold start by:
        1. Using cosine similarity on profile embeddings (Content-based)
        2. Blending with Podchaser global rankings
        """
        # Logic for vector similarity search using FAISS or similar
        pass
