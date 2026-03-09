from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session

from storage.database import get_db
from storage.vector_search import VectorSearch
from embeddings.generator import EmbeddingGenerator


def get_vector_search(db: Session = Depends(get_db)) -> VectorSearch:
    """VectorSearch using the request's DB session."""
    return VectorSearch(db)


@lru_cache(maxsize=1)
def get_embedding_generator() -> EmbeddingGenerator:
    """Create EmbeddingGenerator once, reuse for all requests."""
    return EmbeddingGenerator()