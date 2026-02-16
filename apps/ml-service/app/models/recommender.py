import torch
import torch.nn as nn
import torch.nn.functional as F

class NCFModel(nn.Module):
    """
    Neural Collaborative Filtering (NCF) Model
    Combines Matrix Factorization (MF) and Multi-Layer Perceptron (MLP).
    """
    def __init__(self, num_users, num_items, embedding_size=32, layers=[64, 32, 16, 8]):
        super(NCFModel, self).__init__()
        
        # MF Part
        self.mf_user_embed = nn.Embedding(num_users, embedding_size)
        self.mf_item_embed = nn.Embedding(num_items, embedding_size)
        
        # MLP Part
        self.mlp_user_embed = nn.Embedding(num_users, embedding_size)
        self.mlp_item_embed = nn.Embedding(num_items, embedding_size)
        
        mlp_layers = []
        input_size = embedding_size * 2
        for i in layers:
            mlp_layers.append(nn.Linear(input_size, i))
            mlp_layers.append(nn.ReLU())
            mlp_layers.append(nn.Dropout(p=0.2))
            input_size = i
        self.mlp_network = nn.Sequential(*mlp_layers)
        
        # Merge Layer
        self.final_layer = nn.Linear(layers[-1] + embedding_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, user_indices, item_indices):
        # MF Path
        mf_user = self.mf_user_embed(user_indices)
        mf_item = self.mf_item_embed(item_indices)
        mf_vector = torch.mul(mf_user, mf_item)
        
        # MLP Path
        mlp_user = self.mlp_user_embed(user_indices)
        mlp_item = self.mlp_item_embed(item_indices)
        mlp_vector = torch.cat([mlp_user, mlp_item], dim=-1)
        mlp_vector = self.mlp_network(mlp_vector)
        
        # Concatenate both paths
        vector = torch.cat([mf_vector, mlp_vector], dim=-1)
        prediction = self.final_layer(vector)
        return self.sigmoid(prediction)

class ContentEncoder(nn.Module):
    """
    Encodes podcast/guest metadata (text embeddings) into a hidden space.
    """
    def __init__(self, input_dim=768, hidden_dim=256, output_dim=64):
        super(ContentEncoder, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim)
        )
    
    def forward(self, x):
        return self.net(x)
