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

def get_embedding(text: str, is_query: bool = True):
    """
    Generates embedding locally using sentence-transformers.
    BGE models require 'Represent this sentence for searching relevant passages:' 
    ONLY for queries. Documents/passages should be embedded as-is.
    """
    model = get_model()
    
    # Ensure text is a string and handle empty cases
    if not text or not isinstance(text, str):
        text = "None"
        
    if is_query:
        if not text.startswith("Represent this sentence for searching relevant passages:"):
            text = f"Represent this sentence for searching relevant passages: {text}"
    else:
        # For documents, ensure the prefix is NOT there
        if text.startswith("Represent this sentence for searching relevant passages:"):
            text = text.replace("Represent this sentence for searching relevant passages:", "").strip()
        
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
