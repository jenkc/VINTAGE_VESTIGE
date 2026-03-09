"""
Unit tests for embeddings/generator.py and embeddings/models.py

Tests load_image(), embedding dimensions, determinism, and edge cases.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from PIL import Image
import base64
from io import BytesIO


# ---- load_image tests (no model loading required) ----


class TestLoadImage:

    def test_valid_png_data_url(self, valid_data_url):
        from embeddings.generator import load_image
        result = load_image(valid_data_url)
        assert isinstance(result, Image.Image)
        assert result.size == (1, 1)

    def test_none_returns_none(self):
        from embeddings.generator import load_image
        assert load_image(None) is None

    def test_empty_string_returns_none(self):
        from embeddings.generator import load_image
        assert load_image("") is None

    def test_non_data_url_returns_none(self, invalid_data_url):
        from embeddings.generator import load_image
        assert load_image(invalid_data_url) is None

    def test_pil_image_passthrough(self):
        from embeddings.generator import load_image
        img = Image.new("RGB", (3, 3), color=(255, 0, 0))
        result = load_image(img)
        assert result is img

    def test_jpeg_data_url(self):
        from embeddings.generator import load_image
        img = Image.new("RGB", (2, 2), color=(0, 128, 255))
        buf = BytesIO()
        img.save(buf, format="JPEG")
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"
        result = load_image(data_url)
        assert isinstance(result, Image.Image)
        assert result.size == (2, 2)


# ---- EmbeddingGenerator with mocked models (fast unit tests) ----


class TestEmbeddingGeneratorMocked:

    @pytest.fixture(autouse=True)
    def _mock_models(self):
        """Mock the models singleton to avoid loading real models."""
        mock = MagicMock()
        mock.encode_text.return_value = np.random.randn(384).astype(np.float32)
        mock.encode_image.return_value = np.random.randn(512).astype(np.float32)

        with patch("embeddings.generator.models", mock):
            from embeddings.generator import EmbeddingGenerator
            self.generator = EmbeddingGenerator()
            self.generator.models = mock
            self.mock_models = mock
            yield

    def test_generate_text_embedding_calls_model(self):
        result = self.generator.generate_text_embedding("vintage dress")
        self.mock_models.encode_text.assert_called_once_with("vintage dress")
        assert result.shape == (384,)

    def test_generate_product_embeddings_text_only(self):
        product_data = {"title": "Silk Gown", "description": "A beautiful dress"}
        result = self.generator.generate_product_embeddings(product_data)
        assert "text_embedding" in result
        self.mock_models.encode_text.assert_called_once()

    def test_generate_product_embeddings_no_image_when_missing(self):
        product_data = {"title": "Test", "description": "Test desc"}
        result = self.generator.generate_product_embeddings(product_data)
        assert "image_embedding" not in result

    def test_generate_product_embeddings_empty_text(self):
        product_data = {"title": "", "description": ""}
        result = self.generator.generate_product_embeddings(product_data)
        assert "text_embedding" not in result

    def test_generate_product_embeddings_concatenates_title_desc(self):
        product_data = {"title": "Silk Gown", "description": "1920s evening wear"}
        self.generator.generate_product_embeddings(product_data)
        call_args = self.mock_models.encode_text.call_args[0][0]
        assert "Silk Gown" in call_args
        assert "1920s evening wear" in call_args

    def test_data_url_image_decoded_before_encoding(self, valid_data_url):
        product_data = {
            "title": "Test",
            "description": "Test",
            "primary_image": valid_data_url,
        }
        self.generator.generate_product_embeddings(product_data)
        call_args = self.mock_models.encode_image.call_args[0][0]
        assert isinstance(call_args, Image.Image)

    def test_image_encoding_failure_sets_none(self):
        self.mock_models.encode_image.side_effect = Exception("download failed")
        product_data = {
            "title": "Test",
            "description": "desc",
            "primary_image": "https://broken.url/img.jpg",
        }
        result = self.generator.generate_product_embeddings(product_data)
        assert result.get("image_embedding") is None


# ---- Real model tests (slow, but validate actual dimensions) ----


@pytest.mark.slow
class TestEmbeddingDimensions:
    """Load real models. Only run with `pytest -m slow`."""

    def test_text_embedding_is_384_dim(self, embedding_generator):
        emb = embedding_generator.generate_text_embedding("vintage dress")
        assert emb.shape == (384,)

    def test_text_embedding_is_numpy_array(self, embedding_generator):
        emb = embedding_generator.generate_text_embedding("test")
        assert isinstance(emb, np.ndarray)

    def test_text_embedding_deterministic(self, embedding_generator):
        emb1 = embedding_generator.generate_text_embedding("1920s flapper dress")
        emb2 = embedding_generator.generate_text_embedding("1920s flapper dress")
        np.testing.assert_array_almost_equal(emb1, emb2, decimal=5)

    def test_different_text_different_embedding(self, embedding_generator):
        emb1 = embedding_generator.generate_text_embedding("black leather jacket")
        emb2 = embedding_generator.generate_text_embedding("white silk gown")
        cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        assert cos_sim < 0.95

    def test_image_embedding_is_512_dim(self, embedding_generator):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        emb = embedding_generator.generate_image_embedding(img)
        assert emb.shape == (512,)

    def test_long_text_does_not_crash(self, embedding_generator):
        long_text = "vintage " * 500
        emb = embedding_generator.generate_text_embedding(long_text)
        assert emb.shape == (384,)

    def test_unicode_text_handles(self, embedding_generator):
        emb = embedding_generator.generate_text_embedding(
            "robe a la francaise en soie brodee 18eme siecle"
        )
        assert emb.shape == (384,)
