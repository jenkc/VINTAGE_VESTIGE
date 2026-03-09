"""
Integration tests for storage/vector_search.py

Requires PostgreSQL with pgvector embeddings.
"""
import pytest
import numpy as np


class TestVectorEmbeddingsExist:

    def test_text_embeddings_exist(self, db_session):
        from sqlalchemy import text
        count = db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL")
        ).scalar()
        assert count > 0

    def test_image_embeddings_exist(self, db_session):
        from sqlalchemy import text
        count = db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE image_embedding IS NOT NULL")
        ).scalar()
        assert count > 0


class TestVectorSearch:

    def test_text_search_returns_results(self, vector_search, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("vintage dress")
        results = vector_search.search_text(query_vector, limit=5)
        assert len(results) == 5

    def test_search_result_has_required_fields(self, vector_search, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("silk gown")
        results = vector_search.search_text(query_vector, limit=1)
        result = results[0]
        assert "id" in result
        assert "score" in result
        assert "title" in result
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

    def test_search_respects_limit(self, vector_search, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("coat")
        for limit in [1, 3, 10]:
            results = vector_search.search_text(query_vector, limit=limit)
            assert len(results) == limit

    def test_search_results_ordered_by_score(self, vector_search, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("embroidered jacket")
        results = vector_search.search_text(query_vector, limit=10)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_image_search_returns_results(self, vector_search, embedding_generator):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        query_vector = embedding_generator.generate_image_embedding(img)
        results = vector_search.search_image(query_vector, limit=5)
        assert len(results) == 5
