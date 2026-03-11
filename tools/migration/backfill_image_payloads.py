"""
Backfill vintage_images Qdrant payloads with enrichment data from Postgres.

The image embedding script originally stored only 12 basic fields.
This script adds the missing enrichment fields (style_tags, colors,
material, vibe, etc.) to match the vintage_text payload shape,
WITHOUT re-uploading vectors.

Uses client.set_payload() which merges new fields into existing payloads.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product
from tools.migration.vector_db import VectorDB


def _json_field(value):
    """Parse a JSON TEXT column into a list, or return [] if empty/null."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def build_full_payload(product: Product) -> dict:
    """Build the canonical payload dict matching vintage_text format."""
    return {
        'product_id': product.id,
        'platform': product.platform,
        'title': product.title,
        'category': product.category,
        'era': product.era,
        'decade': product.decade,
        'style_tags': _json_field(product.style_tags),
        'colors': _json_field(product.colors),
        'material': product.material,
        'garment_type': product.garment_type,
        'vibe': product.vibe,
        'fit_style': product.fit_style,
        'occasion': product.occasion,
        'ai_description': product.ai_description,
        'price': product.price,
        'primary_image': product.primary_image,
        'culture': product.culture,
        'object_date': product.object_date,
        'fp_category': product.fp_category,
        'nickname': product.nickname,
        'silhouette': product.silhouette,
        'neckline': product.neckline,
        'waistline': product.waistline,
        'length': product.length,
        'sleeve_length': product.sleeve_length,
        'opening_type': product.opening_type,
        'textile_pattern': product.textile_pattern,
        'textile_finishing': _json_field(product.textile_finishing),
        'garment_parts': _json_field(product.garment_parts),
        'decorations': _json_field(product.decorations),
    }


def backfill_image_payloads():
    print("\n" + "=" * 60)
    print("BACKFILL VINTAGE_IMAGES PAYLOADS")
    print("=" * 60)

    db = SessionLocal()
    vector_db = VectorDB()

    # Get all point IDs currently in vintage_images
    existing_ids = set()
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

    print(f"\nPoints in vintage_images: {len(existing_ids)}")

    if not existing_ids:
        print("No points to backfill.")
        db.close()
        return

    # Load matching products from Postgres
    products = db.query(Product).filter(Product.id.in_(existing_ids)).all()
    product_map = {p.id: p for p in products}

    print(f"Matching products in Postgres: {len(products)}")

    missing_in_pg = existing_ids - set(product_map.keys())
    if missing_in_pg:
        print(f"Warning: {len(missing_in_pg)} Qdrant points have no Postgres match")

    if '--yes' not in sys.argv:
        confirm = input(f"\nBackfill {len(product_map)} payloads? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            db.close()
            return
    else:
        print("\n  [auto-confirmed with --yes]")

    # Backfill using set_payload (merges, doesn't replace vectors)
    updated = 0
    for i, (pid, product) in enumerate(product_map.items(), 1):
        payload = build_full_payload(product)
        vector_db.client.set_payload(
            collection_name='vintage_images',
            payload=payload,
            points=[pid],
        )
        updated += 1
        if i % 50 == 0 or i == len(product_map):
            print(f"  [{i}/{len(product_map)}] updated")

    print(f"\nDone. Updated {updated} payloads in vintage_images.")

    # Verify a sample
    sample_id = next(iter(product_map.keys()))
    sample = vector_db.client.retrieve(
        collection_name='vintage_images',
        ids=[sample_id],
        with_payload=True,
        with_vectors=False,
    )
    if sample:
        keys = sorted(sample[0].payload.keys())
        print(f"\nSample point {sample_id} now has {len(keys)} payload fields:")
        print(f"  {', '.join(keys)}")

    db.close()


if __name__ == '__main__':
    backfill_image_payloads()
