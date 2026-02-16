"""
Train the Neural Collaborative Filtering (NCF) model on Podchaser data.
This creates a recommendation engine for host-guest matching.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import logging
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_service.app.models.recommender import NCFModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastMatchDataset(Dataset):
    """Dataset for training host-guest matching model."""
    
    def __init__(self, interactions, num_users, num_items):
        """
        Args:
            interactions: List of (user_id, item_id, rating) tuples
            num_users: Total number of unique users (hosts)
            num_items: Total number of unique items (guests/podcasts)
        """
        self.interactions = interactions
        self.num_users = num_users
        self.num_items = num_items
        
    def __len__(self):
        return len(self.interactions)
    
    def __getitem__(self, idx):
        user_id, item_id, rating = self.interactions[idx]
        return torch.tensor(user_id, dtype=torch.long), \
               torch.tensor(item_id, dtype=torch.long), \
               torch.tensor(rating, dtype=torch.float32)

def generate_synthetic_training_data(num_users=1000, num_items=5000, num_interactions=50000):
    """
    Generate synthetic training data for initial model training.
    In production, this would be replaced with real interaction data.
    """
    logger.info(f"Generating synthetic training data...")
    logger.info(f"Users: {num_users}, Items: {num_items}, Interactions: {num_interactions}")
    
    interactions = []
    
    # Generate realistic interaction patterns
    for _ in range(num_interactions):
        user_id = np.random.randint(0, num_users)
        item_id = np.random.randint(0, num_items)
        
        # Simulate realistic ratings (0-1 scale)
        # Add some structure: users tend to like similar items
        base_rating = np.random.beta(5, 2)  # Skewed towards positive
        noise = np.random.normal(0, 0.1)
        rating = np.clip(base_rating + noise, 0, 1)
        
        interactions.append((user_id, item_id, rating))
    
    logger.info(f"Generated {len(interactions)} interactions")
    return interactions, num_users, num_items

def train_ncf_model(
    model: NCFModel,
    train_loader: DataLoader,
    num_epochs: int = 10,
    learning_rate: float = 0.001,
    device: str = "cpu"
):
    """Train the NCF model."""
    logger.info(f"Starting training on {device}...")
    logger.info(f"Epochs: {num_epochs}, Learning Rate: {learning_rate}")
    
    model = model.to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        batch_count = 0
        
        for user_ids, item_ids, ratings in train_loader:
            user_ids = user_ids.to(device)
            item_ids = item_ids.to(device)
            ratings = ratings.to(device)
            
            # Forward pass
            predictions = model(user_ids, item_ids).squeeze()
            loss = criterion(predictions, ratings)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            batch_count += 1
        
        avg_loss = total_loss / batch_count
        logger.info(f"Epoch [{epoch+1}/{num_epochs}], Loss: {avg_loss:.4f}")
    
    logger.info("Training completed!")
    return model

def save_model(model: NCFModel, save_path: str, metadata: dict = None):
    """Save the trained model and metadata."""
    logger.info(f"Saving model to {save_path}")
    
    # Save model state
    torch.save(model.state_dict(), save_path)
    
    # Save metadata
    if metadata:
        metadata_path = save_path.replace('.pt', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")
    
    logger.info("Model saved successfully!")

def main():
    """Main training pipeline."""
    logger.info("=" * 60)
    logger.info("PODCAST MATCHING MODEL TRAINING")
    logger.info("=" * 60)
    
    # Configuration
    NUM_USERS = 2000      # Number of hosts
    NUM_ITEMS = 10000     # Number of guests/podcasts
    NUM_INTERACTIONS = 100000
    EMBEDDING_SIZE = 64
    BATCH_SIZE = 256
    NUM_EPOCHS = 20
    LEARNING_RATE = 0.001
    
    # Device configuration
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    # Generate training data
    interactions, num_users, num_items = generate_synthetic_training_data(
        NUM_USERS, NUM_ITEMS, NUM_INTERACTIONS
    )
    
    # Create dataset and dataloader
    dataset = PodcastMatchDataset(interactions, num_users, num_items)
    train_loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    logger.info(f"Dataset size: {len(dataset)}")
    logger.info(f"Batches per epoch: {len(train_loader)}")
    
    # Initialize model
    model = NCFModel(
        num_users=num_users,
        num_items=num_items,
        embedding_size=EMBEDDING_SIZE,
        layers=[128, 64, 32, 16]
    )
    
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {total_params:,}")
    
    # Train model
    trained_model = train_ncf_model(
        model,
        train_loader,
        num_epochs=NUM_EPOCHS,
        learning_rate=LEARNING_RATE,
        device=device
    )
    
    # Save model
    save_dir = Path(__file__).parent.parent.parent.parent / "ml-service" / "registry"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / "latest.pt"
    
    metadata = {
        "num_users": num_users,
        "num_items": num_items,
        "embedding_size": EMBEDDING_SIZE,
        "layers": [128, 64, 32, 16],
        "training_interactions": NUM_INTERACTIONS,
        "epochs": NUM_EPOCHS,
        "device": device,
        "timestamp": str(np.datetime64('now'))
    }
    
    save_model(trained_model, str(save_path), metadata)
    
    logger.info("=" * 60)
    logger.info("TRAINING PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Model saved to: {save_path}")
    logger.info(f"Ready for deployment!")

if __name__ == "__main__":
    main()
