from functools import lru_cache

from storage.vector_db import VectorDB
from embeddings.generator import EmbeddingGenerator

@lru_cache(maxsize=1)
def get_vector_db() -> VectorDB:
    """Create VectorDB once, reuse for all requests."""
    return VectorDB()

@lru_cache(maxsize=1)
def get_embedding_generator() -> EmbeddingGenerator:
    """Create EmbeddingGenerator once, reuse for all requests.
       This loads the ML models (~30 seconds on first call)
    """
    return EmbeddingGenerator()