import torch
import os
from app.models.recommender import NCFModel

def generate_dummy():
    os.makedirs("registry", exist_ok=True)
    model = NCFModel(num_users=10000, num_items=10000)
    torch.save(model.state_dict(), "registry/latest.pt")
    print("Dummy model generated at registry/latest.pt")

if __name__ == "__main__":
    generate_dummy()
