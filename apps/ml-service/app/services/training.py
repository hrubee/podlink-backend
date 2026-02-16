import torch
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import pandas as pd
import os
import datetime
from app.models.recommender import NCFModel

class InteractionDataset(Dataset):
    def __init__(self, user_ids, item_ids, ratings):
        self.users = torch.tensor(user_ids, dtype=torch.long)
        self.items = torch.tensor(item_ids, dtype=torch.long)
        self.ratings = torch.tensor(ratings, dtype=torch.float)
        
    def __len__(self):
        return len(self.users)
        
    def __getitem__(self, idx):
        return self.users[idx], self.items[idx], self.ratings[idx]

class Trainer:
    def __init__(self, model, lr=0.001):
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=lr)
        self.criterion = nn.BCELoss()

    async def train_epoch(self, dataloader):
        self.model.train()
        total_loss = 0
        for users, items, ratings in dataloader:
            self.optimizer.zero_grad()
            outputs = self.model(users, items).squeeze()
            loss = self.criterion(outputs, ratings)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / len(dataloader)

    def save_to_registry(self, version_name=None):
        if not version_name:
            version_name = f"model_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        save_path = f"registry/{version_name}"
        torch.save(self.model.state_of_dict(), save_path)
        # Link current model as latest
        latest_path = "registry/latest.pt"
        if os.path.exists(latest_path):
            os.remove(latest_path)
        torch.save(self.model.state_dict(), latest_path)
        return save_path
