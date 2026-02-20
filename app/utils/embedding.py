# app/utils/embedding.py
import os
from sentence_transformers import SentenceTransformer

# Singleton model loader
_model = None

def get_model():
    global _model
    if _model is None:
        model_name = "BAAI/bge-small-en-v1.5"
        print(f"Loading local embedding model: {model_name}...")
        _model = SentenceTransformer(model_name)
    return _model

def get_embedding(text: str):
    """
    Generates embedding locally using sentence-transformers.
    """
    model = get_model()
    
    # Ensure text is a string and handle empty cases
    if not text or not isinstance(text, str):
        text = "None"
        
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
