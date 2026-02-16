"""
Pre-download ML models during Docker build to avoid runtime downloads.
"""
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models():
    """Download all required models to cache."""
    model_name = "all-MiniLM-L6-v2"
    
    logger.info(f"Downloading model: {model_name}")
    model = SentenceTransformer(model_name)
    logger.info(f"Successfully downloaded {model_name}")
    logger.info(f"Model dimension: {model.get_sentence_embedding_dimension()}")

if __name__ == "__main__":
    download_models()
