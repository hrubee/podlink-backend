"""
Hybrid Ranker — Content-Based + NCF Blended

Scoring breakdown (content-based, used when NCF has insufficient data):
  - Language match:          0.20  (hard filter — critical)
  - Topic overlap:           0.25  (Jaccard similarity)
  - Bio semantic similarity: 0.20  (sentence-transformer cosine)
  - Engagement style match:  0.10  (overlap)
  - Interview format compat: 0.08  (exact or 'both')
  - Fee compatibility:       0.07  (free/paid/negotiable)
  - Episode length pref:     0.05  (exact or adjacent)
  - Content rating compat:   0.05  (clean/explicit/both)

NCF blend weight increases with interaction data:
  - <50 interactions:   NCF 0%,  content 100%
  - 50-200:             NCF 20%, content 80%
  - 200-500:            NCF 40%, content 60%
  - 500-1000:           NCF 60%, content 40%
  - 1000+:              NCF 75%, content 25%
"""
import numpy as np
import torch
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

REGISTRY_DIR = "registry"
METADATA_PATH = os.path.join(REGISTRY_DIR, "model_metadata.json")
LATEST_MODEL_PATH = os.path.join(REGISTRY_DIR, "latest.pt")
ID_MAP_PATH = os.path.join(REGISTRY_DIR, "id_map.json")


def _ncf_blend_weight(total_interactions: int) -> float:
    """Returns the NCF weight (0.0–0.75) based on available interaction data."""
    if total_interactions < 50:
        return 0.0
    elif total_interactions < 200:
        return 0.20
    elif total_interactions < 500:
        return 0.40
    elif total_interactions < 1000:
        return 0.60
    else:
        return 0.75


def _format_compat(user_fmt: str, cand_fmt: str) -> float:
    if user_fmt == "both" or cand_fmt == "both":
        return 1.0
    return 1.0 if user_fmt == cand_fmt else 0.0


def _fee_compat(user_fee: str, cand_fee: str) -> float:
    if user_fee == "negotiable" or cand_fee == "negotiable":
        return 0.8
    if user_fee == "free" and cand_fee == "free":
        return 1.0
    if user_fee == "paid" and cand_fee == "paid":
        return 1.0
    return 0.2  # mismatch but not impossible


def _length_compat(user_len: str, cand_len: str) -> float:
    order = ["<30", "30-45", "45-60", "60+"]
    if user_len == cand_len:
        return 1.0
    try:
        diff = abs(order.index(user_len) - order.index(cand_len))
        return max(0.0, 1.0 - diff * 0.4)
    except ValueError:
        return 0.5


def _rating_compat(user_r: str, cand_r: str) -> float:
    if user_r == "both" or cand_r == "both":
        return 1.0
    return 1.0 if user_r == cand_r else 0.0


def _topic_jaccard(user_topics: List[str], cand_topics: List[str]) -> float:
    u = set(t.lower() for t in user_topics)
    c = set(t.lower() for t in cand_topics)
    if not u and not c:
        return 0.0
    return len(u & c) / len(u | c)


def _style_overlap(user_styles: List[str], cand_styles: List[str]) -> float:
    u = set(user_styles)
    c = set(cand_styles)
    if not u or not c:
        return 0.5  # neutral if either hasn't specified
    return len(u & c) / max(len(u), 1)


class HybridRanker:
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self._ncf_model = None
        self._id_map = None
        self._model_meta = None
        self._load_ncf()

    def _load_ncf(self):
        """Load NCF model if a trained checkpoint exists."""
        if not os.path.exists(LATEST_MODEL_PATH) or not os.path.exists(METADATA_PATH):
            logger.info("No trained NCF model found — running content-based only.")
            return
        try:
            from app.models.recommender import NCFModel
            with open(METADATA_PATH) as f:
                self._model_meta = json.load(f)
            with open(ID_MAP_PATH) as f:
                raw = json.load(f)
                self._id_map = {
                    "users": {int(k): v for k, v in raw.get("users", {}).items()},
                    "items": {int(k): v for k, v in raw.get("items", {}).items()},
                }
            num_users = self._model_meta["num_users"]
            num_items = self._model_meta["num_items"]
            self._ncf_model = NCFModel(num_users=num_users, num_items=num_items,
                                       embedding_size=64, mlp_layers=[128, 64, 32])
            self._ncf_model.load_state_dict(
                torch.load(LATEST_MODEL_PATH, map_location="cpu")
            )
            self._ncf_model.eval()
            logger.info(f"NCF model loaded: {self._model_meta.get('version')}")
        except Exception as e:
            logger.warning(f"Failed to load NCF model: {e}")
            self._ncf_model = None

    def _get_ncf_scores(self, user_id: int, candidate_ids: List[int]) -> Dict[int, float]:
        """Get NCF scores for all candidates. Returns empty dict if model unavailable."""
        if self._ncf_model is None or self._id_map is None:
            return {}
        try:
            u_idx = self._id_map["users"].get(user_id, 0)
            if u_idx == 0:
                return {}  # User not in training data — cold start

            item_indices = [self._id_map["items"].get(c, 0) for c in candidate_ids]
            user_tensor = torch.tensor([u_idx] * len(candidate_ids), dtype=torch.long)
            item_tensor = torch.tensor(item_indices, dtype=torch.long)

            with torch.no_grad():
                scores = self._ncf_model(user_tensor, item_tensor).squeeze().cpu().numpy()

            if scores.ndim == 0:
                scores = np.array([float(scores)])

            return {cid: float(s) for cid, s in zip(candidate_ids, scores)}
        except Exception as e:
            logger.warning(f"NCF inference error: {e}")
            return {}

    def _content_score(self, user_meta: Dict, cand: Dict) -> float:
        """Compute weighted content-based score between user and candidate."""
        score = 0.0

        # Language (0.20) — critical filter
        u_lang = (user_meta.get("language") or "English").lower()
        c_lang = (cand.get("language") or "English").lower()
        if u_lang == c_lang:
            score += 0.20
        elif u_lang[:2] == c_lang[:2]:
            score += 0.10

        # Topic overlap (0.25)
        score += _topic_jaccard(
            user_meta.get("topics") or [],
            cand.get("topics") or []
        ) * 0.25

        # Bio semantic similarity (0.20)
        if self.vector_store and user_meta.get("bio") and cand.get("bio"):
            try:
                u_emb = self.vector_store.model.encode([user_meta["bio"]], normalize_embeddings=True)
                c_emb = self.vector_store.model.encode([cand["bio"]], normalize_embeddings=True)
                sim = float(np.dot(u_emb[0], c_emb[0]))  # already normalized → cosine
                score += max(0.0, sim) * 0.20
            except Exception:
                score += 0.10  # neutral fallback

        # Engagement style (0.10)
        score += _style_overlap(
            user_meta.get("engagement_style") or [],
            cand.get("engagement_style") or []
        ) * 0.10

        # Interview format (0.08)
        score += _format_compat(
            user_meta.get("interview_format") or "both",
            cand.get("interview_format") or "both"
        ) * 0.08

        # Fee compatibility (0.07)
        score += _fee_compat(
            user_meta.get("fee_expectation") or "free",
            cand.get("fee_expectation") or "free"
        ) * 0.07

        # Episode length (0.05)
        score += _length_compat(
            user_meta.get("episode_length_pref") or "45-60",
            cand.get("episode_length_pref") or "45-60"
        ) * 0.05

        # Content rating (0.05)
        score += _rating_compat(
            user_meta.get("content_rating") or "clean",
            cand.get("content_rating") or "clean"
        ) * 0.05

        return round(score, 4)

    def rank(
        self,
        user_id: int,
        user_metadata: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        total_interactions: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Main ranking function. Returns candidates sorted by hybrid score descending.
        Each result: {"id": int, "score": float, "content_score": float, "ncf_score": float}
        """
        if not candidates:
            return []

        ncf_weight = _ncf_blend_weight(total_interactions)
        content_weight = 1.0 - ncf_weight

        candidate_ids = [c["id"] for c in candidates]
        ncf_scores = self._get_ncf_scores(user_id, candidate_ids) if ncf_weight > 0 else {}

        results = []
        for cand in candidates:
            cid = cand["id"]
            c_score = self._content_score(user_metadata, cand)
            n_score = ncf_scores.get(cid, 0.0)
            hybrid = content_weight * c_score + ncf_weight * n_score

            results.append({
                "id": cid,
                "score": round(hybrid, 4),
                "content_score": c_score,
                "ncf_score": round(n_score, 4),
                "ncf_weight": ncf_weight,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
