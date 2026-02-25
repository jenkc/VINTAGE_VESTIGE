"""
Integration tests for storage/vector_db.py

Requires a running Qdrant instance with existing collections.
"""
import pytest
import numpy as np


class TestVectorDBCollections:

    def test_collections_exist(self, vector_db):
        info = vector_db.get_collection_info()
        assert "vintage_images" in info
        assert "vintage_text" in info

    def test_image_collection_has_vectors(self, vector_db):
        info = vector_db.get_collection_info()
        count = info["vintage_images"].get("points_count") or info["vintage_images"].get("vectors_count") or 0
        assert count > 0

    def test_text_collection_has_vectors(self, vector_db):
        info = vector_db.get_collection_info()
        count = info["vintage_text"].get("points_count") or info["vintage_text"].get("vectors_count") or 0
        assert count > 0


class TestVectorDBSearch:

    def test_text_search_returns_results(self, vector_db, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("vintage dress")
        results = vector_db.search_similar(
            collection="vintage_text",
            query_vector=query_vector,
            limit=5,
        )
        assert len(results) == 5

    def test_search_result_has_required_fields(self, vector_db, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("silk gown")
        results = vector_db.search_similar(
            collection="vintage_text",
            query_vector=query_vector,
            limit=1,
        )
        result = results[0]
        assert "id" in result
        assert "score" in result
        assert "title" in result
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

    def test_search_respects_limit(self, vector_db, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("coat")
        for limit in [1, 3, 10, 20]:
            results = vector_db.search_similar(
                collection="vintage_text",
                query_vector=query_vector,
                limit=limit,
            )
            assert len(results) == limit

    def test_search_results_ordered_by_score(self, vector_db, embedding_generator):
        query_vector = embedding_generator.generate_text_embedding("embroidered jacket")
        results = vector_db.search_similar(
            collection="vintage_text",
            query_vector=query_vector,
            limit=10,
        )
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_image_search_returns_results(self, vector_db, embedding_generator):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        query_vector = embedding_generator.generate_image_embedding(img)
        results = vector_db.search_similar(
            collection="vintage_images",
            query_vector=query_vector,
            limit=5,
        )
        assert len(results) == 5

    def test_upsert_and_retrieve_roundtrip(self, vector_db):
        """Upsert a test vector, search for it, then clean up."""
        test_id = 999999
        test_vector = np.random.randn(384).astype(np.float32)
        test_vector = test_vector / np.linalg.norm(test_vector)

        metadata = {"title": "PYTEST_TEST_ITEM", "price": 0.0, "platform": "test"}

        # Upsert
        vector_db.client.upsert(
            collection_name="vintage_text",
            points=[{
                "id": test_id,
                "vector": test_vector.tolist(),
                "payload": metadata,
            }],
        )

        try:
            # Retrieve by searching with the same vector
            results = vector_db.search_similar(
                collection="vintage_text",
                query_vector=test_vector,
                limit=1,
            )
            assert results[0]["id"] == test_id
            assert results[0]["title"] == "PYTEST_TEST_ITEM"
        finally:
            # Always clean up
            from qdrant_client.models import PointIdsList
            vector_db.client.delete(
                collection_name="vintage_text",
                points_selector=PointIdsList(points=[test_id]),
            )
