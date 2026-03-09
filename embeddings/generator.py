from embeddings.models import models
from storage.database import SessionLocal, Product
import numpy as np
from datetime import datetime
import base64
import requests
from io import BytesIO
from PIL import Image


def load_image(image_ref):
    """Load image from data URL, HTTP URL, or PIL Image."""
    if not image_ref:
        return None
    if isinstance(image_ref, Image.Image):
        return image_ref
    if isinstance(image_ref, str):
        if image_ref.startswith('data:image'):
            header, encoded = image_ref.split(',', 1)
            return Image.open(BytesIO(base64.b64decode(encoded)))
        elif image_ref.startswith('http'):
            resp = requests.get(image_ref, timeout=15)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content))
    return None


class EmbeddingGenerator:
    """Generate embeddings for products"""

    def __init__(self):
        self.models = models

    def generate_product_embeddings(self, product_data):
        """
        Generate embeddings for a product

        Args:
            product_data: dict with 'primary_image', 'title', 'description'

        Returns:
            dict with 'image_embedding', 'text_embedding'
        """
        embeddings = {}

        # Image embedding
        if product_data.get('primary_image'):
            try:
                image_input = load_image(product_data['primary_image'])
                if image_input is None:
                    raise ValueError("Could not load image")

                image_emb = self.models.encode_image(image_input)
                embeddings['image_embedding'] = image_emb

            except Exception as e:
                print(f"  Image embedding failed: {e}")
                embeddings['image_embedding'] = None

        # Text embedding
        text_parts = []
        if product_data.get('title'):
            text_parts.append(product_data['title'])
        if product_data.get('description'):
            text_parts.append(product_data['description'])

        text = " ".join(text_parts)

        if text:
            text_emb = self.models.encode_text(text)
            embeddings['text_embedding'] = text_emb

        return embeddings

    def generate_text_embedding(self, text):
        """Generate embedding for search query text"""
        return self.models.encode_text(text)

    def generate_image_embedding(self, image_input):
        """Generate embedding for search query image"""
        return self.models.encode_image(image_input)


def generate_embeddings_for_database(limit=None):
    """
    Generate embeddings for all products in database

    Args:
        limit: Optional limit on number of products to process
    """
    db = SessionLocal()
    generator = EmbeddingGenerator()

    # Get enriched products without text embeddings
    query = db.query(Product).filter(
        Product.enriched_at != None,
        Product.text_embedding == None,
    )
    if limit:
        query = query.limit(limit)

    products = query.all()
    total = len(products)

    print(f"Generating embeddings for {total} products...\n")

    embeddings_data = []

    for i, product in enumerate(products):
        try:
            print(f"[{i+1}/{total}] Processing: {product.title[:50]}...")

            # Text embedding from enriched_text (rich text with vibes, era, structure)
            # Falls back to title+description if enriched_text not available
            text_source = product.enriched_text or f"{product.title or ''} {product.description or ''}".strip()

            embeddings = {}
            if text_source:
                embeddings['text_embedding'] = generator.generate_text_embedding(text_source)

            # Image embedding
            if product.primary_image and product.image_embedding is None:
                try:
                    pil_image = load_image(product.primary_image)
                    if pil_image:
                        embeddings['image_embedding'] = generator.generate_image_embedding(pil_image)
                except Exception as e:
                    print(f"  Image embedding failed: {e}")

            # Collect embedding results
            embeddings_data.append({
                'product_id': str(product.id),
                'image_embedding': embeddings.get('image_embedding'),
                'text_embedding': embeddings.get('text_embedding'),
            })

            # Mark as embedded
            product.embedded_at = datetime.utcnow()

            if (i + 1) % 10 == 0:
                db.commit()
                print(f"   Checkpoint: {i+1} products processed\n")

        except Exception as e:
            print(f"  Error: {e}\n")
            continue

    db.commit()
    db.close()

    print(f"\nGenerated embeddings for {len(embeddings_data)} products!")
    print(f"Ready to store in database\n")

    # Write embeddings to product columns
    db = SessionLocal()
    print(f"Writing embeddings to product columns...")
    for item in embeddings_data:
        product = db.query(Product).filter(
            Product.id == int(item['product_id'])
        ).first()
        if product:
            if item.get('text_embedding') is not None:
                product.text_embedding = item['text_embedding'].tolist()
            if item.get('image_embedding') is not None:
                product.image_embedding = item['image_embedding'].tolist()
    db.commit()
    db.close()
    print(f"Stored {len(embeddings_data)} embeddings in pgvector!\n")


    return embeddings_data


if __name__ == "__main__":
    # Test embedding generation with 5 products
    embeddings_data = generate_embeddings_for_database()

    print(f"Sample embedding data:")
    if embeddings_data:
        sample = embeddings_data[0]
        print(f"   Product ID: {sample['product_id']}")
        if sample['image_embedding'] is not None:
            print(f"   Image embedding shape: {sample['image_embedding'].shape}")
        if sample['text_embedding'] is not None:
            print(f"   Text embedding shape: {sample['text_embedding'].shape}")
