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
from embeddings.generator import EmbeddingGenerator, load_image
import time

def generate_image_embeddings():
    print("\n" + "=" * 60)
    print("GENERATING IMAGE EMBEDDINGS (CLIP)")
    print("=" * 60)

    db = SessionLocal()
    generator = EmbeddingGenerator()

    # Products with images but no image embedding
    missing = db.query(Product).filter(
        Product.primary_image != None,
        Product.image_embedding == None,
    ).all()

    print(f"\nMissing image embeddings: {len(missing)}")

    if not missing:
        print("All image embeddings are up to date!")
        db.close()
        return

    if '--yes' not in sys.argv:
        confirm = input(f"\nGenerate {len(missing)} image embeddings? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            db.close()
            return

    success = 0
    failed = 0

    for i, product in enumerate(missing, 1):
        try:
            print(f"[{i}/{len(missing)}] {product.title[:50]}...")

            image = load_image(product.primary_image)
            if image is None:
                print(f"  Skipped: could not load image")
                failed += 1
                continue

            image_embedding = generator.generate_image_embedding(image)
            product.image_embedding = image_embedding.tolist()

            if i % 10 == 0:
                db.commit()
                print(f"  Checkpoint: {i} processed")

            success += 1

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            failed += 1
            continue

    db.commit()
    db.close()

    print(f"\nDone! Success: {success}, Failed: {failed}")


if __name__ == '__main__':
    generate_image_embeddings()