"""
NCF Model — Neural Collaborative Filtering
Combines Matrix Factorization (MF) + Multi-Layer Perceptron (MLP).
Used as the collaborative filtering component of the hybrid ranker.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class NCFModel(nn.Module):
    def __init__(self, num_users: int, num_items: int, embedding_size: int = 64,
                 mlp_layers: list = None):
        super().__init__()
        if mlp_layers is None:
            mlp_layers = [128, 64, 32]

        # ── MF Path ──────────────────────────────────────────────────────────
        self.mf_user_embed = nn.Embedding(num_users + 1, embedding_size, padding_idx=0)
        self.mf_item_embed = nn.Embedding(num_items + 1, embedding_size, padding_idx=0)

        # ── MLP Path ─────────────────────────────────────────────────────────
        self.mlp_user_embed = nn.Embedding(num_users + 1, embedding_size, padding_idx=0)
        self.mlp_item_embed = nn.Embedding(num_items + 1, embedding_size, padding_idx=0)

        layers = []
        input_size = embedding_size * 2
        for hidden in mlp_layers:
            layers += [nn.Linear(input_size, hidden), nn.ReLU(), nn.Dropout(0.2)]
            input_size = hidden
        self.mlp_network = nn.Sequential(*layers)

        # ── Merge ─────────────────────────────────────────────────────────────
        # MF output = embedding_size, MLP output = last layer size
        self.final_layer = nn.Linear(embedding_size + mlp_layers[-1], 1)
        self.sigmoid = nn.Sigmoid()

        # Weight init
        nn.init.normal_(self.mf_user_embed.weight, std=0.01)
        nn.init.normal_(self.mf_item_embed.weight, std=0.01)
        nn.init.normal_(self.mlp_user_embed.weight, std=0.01)
        nn.init.normal_(self.mlp_item_embed.weight, std=0.01)

    def forward(self, user_indices: torch.Tensor, item_indices: torch.Tensor) -> torch.Tensor:
        # MF path
        mf_user = self.mf_user_embed(user_indices)
        mf_item = self.mf_item_embed(item_indices)
        mf_vector = mf_user * mf_item  # element-wise product

        # MLP path
        mlp_user = self.mlp_user_embed(user_indices)
        mlp_item = self.mlp_item_embed(item_indices)
        mlp_input = torch.cat([mlp_user, mlp_item], dim=-1)
        mlp_vector = self.mlp_network(mlp_input)

        # Merge and predict
        merged = torch.cat([mf_vector, mlp_vector], dim=-1)
        return self.sigmoid(self.final_layer(merged))


class ContentEncoder(nn.Module):
    """
    Encodes rich profile metadata (text embeddings + structured features)
    into a unified latent space for content-based similarity.
    """
    def __init__(self, text_dim: int = 384, structured_dim: int = 16,
                 hidden_dim: int = 128, output_dim: int = 64):
        super().__init__()
        input_dim = text_dim + structured_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
