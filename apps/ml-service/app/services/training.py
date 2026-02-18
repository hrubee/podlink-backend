"""
Training pipeline for the NCF model.

Handles:
- InteractionDataset: wraps like/dislike data with negative sampling
- Trainer: full train loop with BCE loss + Adam
- ID mapping: maps raw DB user/item IDs to contiguous 0-based indices
- Model registry: saves versioned checkpoints + latest.pt symlink
- Negative sampling: for every positive interaction, sample N negatives
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
import json
import os
import logging
from datetime import datetime
from typing import List, Tuple, Dict

from app.models.recommender import NCFModel

logger = logging.getLogger(__name__)

REGISTRY_DIR = "registry"
ID_MAP_PATH = os.path.join(REGISTRY_DIR, "id_map.json")
LATEST_MODEL_PATH = os.path.join(REGISTRY_DIR, "latest.pt")
METADATA_PATH = os.path.join(REGISTRY_DIR, "model_metadata.json")


# ── ID Mapper ─────────────────────────────────────────────────────────────────

class IDMapper:
    """
    Maps raw DB integer IDs (which can be large/sparse) to contiguous
    0-based indices required by nn.Embedding.
    Persisted to disk so inference uses the same mapping as training.
    """
    def __init__(self):
        self.user_map: Dict[int, int] = {}   # raw_id -> embedding_idx
        self.item_map: Dict[int, int] = {}
        self._load()

    def _load(self):
        if os.path.exists(ID_MAP_PATH):
            with open(ID_MAP_PATH) as f:
                data = json.load(f)
            self.user_map = {int(k): v for k, v in data.get("users", {}).items()}
            self.item_map = {int(k): v for k, v in data.get("items", {}).items()}

    def save(self):
        os.makedirs(REGISTRY_DIR, exist_ok=True)
        with open(ID_MAP_PATH, "w") as f:
            json.dump({"users": self.user_map, "items": self.item_map}, f)

    def fit(self, user_ids: List[int], item_ids: List[int]):
        """Build mapping from all unique IDs seen in training data."""
        for uid in set(user_ids):
            if uid not in self.user_map:
                self.user_map[uid] = len(self.user_map) + 1  # 1-based (0 = padding)
        for iid in set(item_ids):
            if iid not in self.item_map:
                self.item_map[iid] = len(self.item_map) + 1
        self.save()

    def get_user(self, raw_id: int) -> int:
        return self.user_map.get(raw_id, 0)  # 0 = unknown (padding)

    def get_item(self, raw_id: int) -> int:
        return self.item_map.get(raw_id, 0)

    @property
    def num_users(self) -> int:
        return len(self.user_map)

    @property
    def num_items(self) -> int:
        return len(self.item_map)


# ── Dataset ───────────────────────────────────────────────────────────────────

class InteractionDataset(Dataset):
    """
    Wraps positive interactions (likes) and generates negative samples.
    Negative sampling ratio: for each positive, sample `neg_ratio` negatives.
    """
    def __init__(self, user_ids: List[int], item_ids: List[int],
                 labels: List[float], all_item_ids: List[int], neg_ratio: int = 4):
        pos_users = np.array(user_ids, dtype=np.int64)
        pos_items = np.array(item_ids, dtype=np.int64)
        pos_labels = np.ones(len(user_ids), dtype=np.float32)

        # Negative sampling
        all_items = np.array(all_item_ids)
        pos_set = set(zip(user_ids, item_ids))
        neg_users, neg_items = [], []
        for u, i in zip(user_ids, item_ids):
            sampled = 0
            attempts = 0
            while sampled < neg_ratio and attempts < neg_ratio * 10:
                neg_i = int(np.random.choice(all_items))
                if (u, neg_i) not in pos_set:
                    neg_users.append(u)
                    neg_items.append(neg_i)
                    sampled += 1
                attempts += 1

        neg_labels = np.zeros(len(neg_users), dtype=np.float32)

        self.users = torch.from_numpy(np.concatenate([pos_users, np.array(neg_users, dtype=np.int64)]))
        self.items = torch.from_numpy(np.concatenate([pos_items, np.array(neg_items, dtype=np.int64)]))
        self.labels = torch.from_numpy(np.concatenate([pos_labels, neg_labels]))

    def __len__(self):
        return len(self.users)

    def __getitem__(self, idx):
        return self.users[idx], self.items[idx], self.labels[idx]


# ── Trainer ───────────────────────────────────────────────────────────────────

class Trainer:
    def __init__(self, model: NCFModel, lr: float = 0.001):
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
        self.criterion = nn.BCELoss()
        self.device = torch.device("cpu")  # Railway has no GPU
        self.model.to(self.device)

    def train_epoch(self, dataloader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for users, items, labels in dataloader:
            users = users.to(self.device)
            items = items.to(self.device)
            labels = labels.to(self.device)

            self.optimizer.zero_grad()
            preds = self.model(users, items).squeeze()
            loss = self.criterion(preds, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / max(len(dataloader), 1)

    def evaluate(self, dataloader: DataLoader) -> float:
        """Returns hit rate @ 10 on validation set."""
        self.model.eval()
        hits = 0
        total = 0
        with torch.no_grad():
            for users, items, labels in dataloader:
                users = users.to(self.device)
                items = items.to(self.device)
                preds = self.model(users, items).squeeze().cpu().numpy()
                hits += int(np.sum(preds > 0.5) == np.sum(labels.numpy() > 0.5))
                total += 1
        return hits / max(total, 1)

    def save_to_registry(self, id_mapper: IDMapper) -> str:
        os.makedirs(REGISTRY_DIR, exist_ok=True)
        version = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        version_path = os.path.join(REGISTRY_DIR, version)

        torch.save(self.model.state_dict(), version_path)
        torch.save(self.model.state_dict(), LATEST_MODEL_PATH)

        # Save metadata for inference
        meta = {
            "version": version,
            "trained_at": datetime.now().isoformat(),
            "num_users": id_mapper.num_users,
            "num_items": id_mapper.num_items,
        }
        with open(METADATA_PATH, "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Model saved: {version_path}")
        return version_path


# ── Full Training Pipeline ────────────────────────────────────────────────────

def run_training(
    interactions: List[Dict],  # [{"actor_id": int, "target_id": int, "type": "like"|"dislike"}]
    epochs: int = 10,
    batch_size: int = 256,
    lr: float = 0.001,
) -> Dict:
    """
    Full training pipeline called by the /train endpoint.
    interactions: list of dicts from the backend DB.
    Returns training summary.
    """
    if len(interactions) < 10:
        return {"status": "skipped", "reason": "Not enough interactions (<10). Need at least 10 likes."}

    # Separate likes (positive) from dislikes (ignored for now — used as negatives later)
    likes = [i for i in interactions if i["type"] == "like"]
    if len(likes) < 5:
        return {"status": "skipped", "reason": "Not enough positive interactions (<5 likes)."}

    user_ids = [i["actor_id"] for i in likes]
    item_ids = [i["target_id"] for i in likes]
    labels = [1.0] * len(likes)

    # Build ID mapping
    id_mapper = IDMapper()
    id_mapper.fit(user_ids, item_ids)

    # Map to embedding indices
    mapped_users = [id_mapper.get_user(u) for u in user_ids]
    mapped_items = [id_mapper.get_item(i) for i in item_ids]
    all_mapped_items = list(id_mapper.item_map.values())

    # Dataset + DataLoader
    dataset = InteractionDataset(mapped_users, mapped_items, labels, all_mapped_items, neg_ratio=4)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

    # Build model
    model = NCFModel(
        num_users=id_mapper.num_users,
        num_items=id_mapper.num_items,
        embedding_size=64,
        mlp_layers=[128, 64, 32]
    )
    trainer = Trainer(model, lr=lr)

    # Train
    losses = []
    for epoch in range(epochs):
        loss = trainer.train_epoch(dataloader)
        losses.append(round(loss, 4))
        logger.info(f"Epoch {epoch+1}/{epochs} — Loss: {loss:.4f}")

    # Save
    path = trainer.save_to_registry(id_mapper)

    return {
        "status": "success",
        "epochs": epochs,
        "interactions_used": len(likes),
        "num_users": id_mapper.num_users,
        "num_items": id_mapper.num_items,
        "final_loss": losses[-1],
        "loss_history": losses,
        "model_path": path,
    }
