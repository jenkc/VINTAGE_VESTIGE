"""
Generate CLIP image embeddings for all products that have images
but are missing from the vintage_images Qdrant collection.

This fills the gap left by enrich_and_reembed_all.py, which only
generates text embeddings.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product
from storage.vector_db import VectorDB
from embeddings.generator import EmbeddingGenerator, decode_data_url
from embeddings.scripts.backfill_image_payloads import build_full_payload
from qdrant_client.models import PointStruct
import time

def generate_image_embeddings():
    print("\n" + "=" * 60)
    print("GENERATING IMAGE EMBEDDINGS (CLIP)")
    print("=" * 60)

    db = SessionLocal()
    vector_db = VectorDB()
    generator = EmbeddingGenerator()

    # Get all products with images
    products = db.query(Product).filter(
        Product.primary_image != None
    ).all()

    # Check which IDs already exist in vintage_images
    existing_ids = set()
    try:
        # Scroll through all points to get existing IDs
        offset = None
        while True:
            result = vector_db.client.scroll(
                collection_name='vintage_images',
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            points, offset = result
            for point in points:
                existing_ids.add(point.id)
            if offset is None:
                break
    except Exception as e:
        print(f"Warning: Could not check existing IDs: {e}")

    # Filter to products missing image embeddings
    missing = [p for p in products if p.id not in existing_ids]

    print(f"\nTotal products with images: {len(products)}")
    print(f"Already in vintage_images: {len(existing_ids)}")
    print(f"Missing image embeddings: {len(missing)}")

    if not missing:
        print("\nAll image embeddings are up to date!")
        db.close()
        return

    if '--yes' not in sys.argv:
        confirm = input(f"\nGenerate {len(missing)} image embeddings? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            db.close()
            return
    else:
        print("\n  [auto-confirmed with --yes]")

    print("\n" + "=" * 60)
    print("Starting image embedding generation...")
    print("=" * 60)

    success = 0
    failed = 0

    for i, product in enumerate(missing, 1):
        try:
            print(f"\n[{i}/{len(missing)}] {product.title[:50]}...")

            # Decode image
            image = decode_data_url(product.primary_image)
            if image is None:
                print(f"  Skipped: could not decode image")
                failed += 1
                continue

            # Generate CLIP embedding
            image_embedding = generator.generate_image_embedding(image)

            # Build full payload matching vintage_text format
            payload = build_full_payload(product)

            # Upsert to Qdrant
            vector_db.client.upsert(
                collection_name='vintage_images',
                points=[PointStruct(
                    id=product.id,
                    vector=image_embedding.tolist(),
                    payload=payload,
                )]
            )

            success += 1
            print(f"  [{product.platform}] Embedded")

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            failed += 1
            continue

    # Summary
    print("\n" + "=" * 60)
    print("IMAGE EMBEDDING COMPLETE")
    print("=" * 60)
    print(f"\n  Success: {success}")
    print(f"  Failed: {failed}")

    # Final counts
    info = vector_db.get_collection_info()
    for name, data in info.items():
        print(f"  {name}: {data}")

    db.close()


if __name__ == '__main__':
    generate_image_embeddings()
