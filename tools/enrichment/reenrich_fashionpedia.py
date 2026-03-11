"""
Re-enrich Fashionpedia items to fill missing creative fields.

Fashionpedia products have expert-annotated structural fields (fp_category,
silhouette, etc.) but are missing creative/bridge fields like culture,
neckline, and sleeve_length. This script uses enrich_creative_only() to
preserve expert annotations while adding the missing fields.

Usage:
  python enrichment/scripts/reenrich_fashionpedia.py [limit] [--yes]

Run from project root.
"""
import sys
import os
import json
import time
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher


def build_existing_fields(product):
    """Build existing_fields dict from expert-annotated product attributes."""
    fields = {}

    # Scalar structural fields
    for key in ('fp_category', 'nickname', 'silhouette', 'neckline', 'waistline',
                'length', 'sleeve_length', 'opening_type', 'textile_pattern'):
        val = getattr(product, key, None)
        if val:
            fields[key] = val

    # JSON list fields
    for key in ('textile_finishing', 'garment_parts', 'decorations'):
        raw = getattr(product, key, None)
        if raw:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list) and parsed:
                    fields[key] = parsed
            except (json.JSONDecodeError, TypeError):
                pass

    return fields


def reenrich_fashionpedia(limit=None):
    """Re-enrich Fashionpedia items with creative fields."""

    print("\n" + "=" * 70)
    print("RE-ENRICHING FASHIONPEDIA ITEMS - CREATIVE FIELDS")
    print("=" * 70)

    db = SessionLocal()
    enricher = ClaudeEnricher()
    generator = EmbeddingGenerator()

    # Get fashionpedia items
    query = db.query(Product).filter(Product.platform == 'fashionpedia')
    if limit:
        query = query.limit(limit)
    products = query.all()

    print(f"\nFashionpedia products to re-enrich: {len(products)}")

    # Check current state
    for field in ('culture', 'neckline', 'sleeve_length'):
        populated = sum(1 for p in products if getattr(p, field, None))
        print(f"  {field}: {populated}/{len(products)}")

    print(f"\nEstimated cost: ${len(products) * 0.015:.2f}")
    print(f"Estimated time: ~{len(products) * 0.6 // 60:.0f} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return

    print("\n" + "=" * 70)
    print("Starting re-enrichment...")
    print("=" * 70)

    success_count = 0
    culture_count = 0
    neckline_count = 0
    sleeve_count = 0
    failed_count = 0

    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product.title[:60]}")

        try:
            existing_fields = build_existing_fields(product)

            enrichment = enricher.enrich_creative_only(
                title=product.title,
                category=product.category,
                existing_fields=existing_fields,
                image_data_url=product.primary_image,
            )

            # Build rich text
            rich_text = enricher.build_rich_text(
                product_data={
                    'title': product.title,
                    'category': product.category,
                },
                enrichment=enrichment,
            )

            # Generate new text embedding
            new_text_embedding = generator.generate_text_embedding(rich_text)

            # Write new text embedding to product column
            product.text_embedding = new_text_embedding.tolist()

            # Update PostgreSQL - creative fields
            product.era = enrichment.get('era')
            product.decade = enrichment.get('decade')
            product.culture = enrichment.get('culture')
            product.style_tags = json.dumps(enrichment.get('style_tags', []))
            product.colors = json.dumps(enrichment.get('colors', []))
            product.material = enrichment.get('material')
            product.garment_type = enrichment.get('garment_type')
            product.vibe = enrichment.get('vibe')
            product.fit_style = enrichment.get('fit_style')
            product.occasion = enrichment.get('occasion')
            product.ai_description = enrichment.get('ai_description')
            product.enriched_text = rich_text

            # Structural fields inferred from image (only if not expert-annotated)
            if enrichment.get('neckline') and not getattr(product, 'neckline', None):
                product.neckline = enrichment['neckline']
            elif enrichment.get('neckline'):
                product.neckline = enrichment['neckline']

            if enrichment.get('sleeve_length') and not getattr(product, 'sleeve_length', None):
                product.sleeve_length = enrichment['sleeve_length']
            elif enrichment.get('sleeve_length'):
                product.sleeve_length = enrichment['sleeve_length']

            product.enriched_at = datetime.now()

            db.commit()
            success_count += 1

            # Track new fields
            if enrichment.get('culture'):
                culture_count += 1
            if enrichment.get('neckline'):
                neckline_count += 1
            if enrichment.get('sleeve_length'):
                sleeve_count += 1

            print(f"  culture: {enrichment.get('culture') or '-'}")
            print(f"  neckline: {enrichment.get('neckline') or '-'} | "
                  f"sleeve: {enrichment.get('sleeve_length') or '-'}")
            print(f"  era: {enrichment.get('era')} | vibe: {enrichment.get('vibe')}")

            # Rate limiting
            time.sleep(0.6)

        except Exception as e:
            print(f"  ERROR: {str(e)[:100]}")
            failed_count += 1
            continue

    # Summary
    print("\n" + "=" * 70)
    print("RE-ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Successfully re-enriched: {success_count}")
    print(f"  Failed:                   {failed_count}")
    print(f"\nNew field coverage:")
    print(f"  culture:      {culture_count}/{success_count}")
    print(f"  neckline:     {neckline_count}/{success_count}")
    print(f"  sleeve_length:{sleeve_count}/{success_count}")

    db.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    limit_val = int(args[0]) if args else None
    reenrich_fashionpedia(limit=limit_val)
