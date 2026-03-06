# app/utils/embedding.py
import os
from sentence_transformers import SentenceTransformer

# Singleton model loader
_model = None

def get_model():
    global _model
    if _model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        print(f"Loading local embedding model: {model_name} (Forced CPU mode)...")
        # Force CPU to save VRAM (user has 2GB GPU vs 16GB RAM)
        _model = SentenceTransformer(model_name, device="cpu")
    return _model

def get_embedding(text: str):
    """
    Generates embedding locally using sentence-transformers.
    """
    model = get_model()
    
    # Ensure text is a string and handle empty cases
    if not text or not isinstance(text, str):
        text = "None"
        
    if not text.startswith("Represent this sentence for searching relevant passages:"):
        text = f"Represent this sentence for searching relevant passages: {text}"
        
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
