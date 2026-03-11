"""
Enrich the remaining unenriched items and diagnose why they weren't enriched.

This script finds all items with enriched_at = NULL, attempts to enrich them,
and reports on items that fail enrichment (likely non-garments).
"""
import sys
import os

# Add scripts directory to path so we can import modules
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, scripts_dir)

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
from enrichment.era_taxonomy import normalize_era, report_unrecognized_eras, export_unrecognized_eras
from datetime import datetime
import json
import time


def enrich_remaining(limit: int = None):
    """Enrich all remaining unenriched items."""

    print("\n" + "=" * 70)
    print("ENRICHING REMAINING UNENRICHED ITEMS")
    print("=" * 70)

    db = SessionLocal()
    enricher = ClaudeEnricher()
    generator = EmbeddingGenerator()

    # Get unenriched items
    query = db.query(Product).filter(Product.enriched_at == None)
    if limit:
        query = query.limit(limit)
    products = query.all()

    print(f"\nUnenriched products: {len(products)}")

    # Group by platform to understand the breakdown
    by_platform = {}
    for p in products:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print("\nBy platform:")
    for platform, count in sorted(by_platform.items(), key=lambda x: x[1], reverse=True):
        print(f"  {platform:20s} {count:4d}")

    # Show sample titles to understand what we're dealing with
    print("\nSample unenriched titles:")
    for p in products[:10]:
        print(f"  [{p.platform}] {p.title[:70]}")

    print(f"\nEstimated cost: ${len(products) * 0.025:.2f}")
    print(f"Estimated time: ~{len(products) * 6 // 60} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return

    print("\n" + "=" * 70)
    print("Starting enrichment...")
    print("=" * 70)

    success_count = 0
    failed_count = 0
    non_garment_count = 0
    failed_items = []
    start_time = time.time()

    for i, product in enumerate(products, 1):
        elapsed = time.time() - start_time
        avg_per_item = elapsed / i if i > 1 else 6
        remaining = avg_per_item * (len(products) - i)
        elapsed_min = elapsed / 60
        remaining_min = remaining / 60
        print(f"\n[{i}/{len(products)}] ({elapsed_min:.1f}m elapsed, ~{remaining_min:.1f}m remaining) {product.title[:60]}")
        print(f"  Platform: {product.platform} | Category: {product.category}")

        try:
            # Determine enrichment path
            has_expert_annotations = (
                product.platform == 'fashionpedia' and product.fp_category is not None
            )

            if has_expert_annotations:
                # Creative-only for Fashionpedia
                existing_fields = {
                    'fp_category': product.fp_category,
                    'nickname': product.nickname,
                    'silhouette': product.silhouette,
                    'neckline': product.neckline,
                    'waistline': product.waistline,
                    'length': product.length,
                    'sleeve_length': product.sleeve_length,
                    'opening_type': product.opening_type,
                    'textile_pattern': product.textile_pattern,
                    'textile_finishing': json.loads(product.textile_finishing) if product.textile_finishing else [],
                    'garment_parts': json.loads(product.garment_parts) if product.garment_parts else [],
                    'decorations': json.loads(product.decorations) if product.decorations else [],
                }
                enrichment = enricher.enrich_creative_only(
                    title=product.title,
                    category=product.category or product.fp_category or '',
                    existing_fields=existing_fields,
                    image_data_url=product.primary_image
                )
                print(f"  [creative-only]")
            else:
                # Full enrichment
                enrichment = enricher.enrich_product(
                    title=product.title,
                    category=product.category,
                    color=product.color,
                    season=product.season,
                    year=product.year,
                    material=product.material,
                    pattern=product.pattern,
                    culture=product.culture,
                    period=product.period,
                    era=product.era,
                    object_date=product.object_date,
                    image_data_url=product.primary_image
                )
                print(f"  [full enrichment]")

            # Check if enrichment succeeded (has meaningful data)
            has_content = (
                enrichment.get('era') or
                enrichment.get('fp_category') or
                enrichment.get('garment_type')
            )

            if not has_content:
                print(f"  ⚠ Enrichment returned empty - likely not a garment")
                non_garment_count += 1
                failed_items.append({
                    'id': product.id,
                    'platform': product.platform,
                    'title': product.title,
                    'category': product.category,
                    'reason': 'empty enrichment'
                })
                continue

            # Build rich text
            rich_text = enricher.build_rich_text(
                product_data={
                    'title': product.title,
                    'category': product.category
                },
                enrichment=enrichment
            )

            # Generate text embedding
            new_text_embedding = generator.generate_text_embedding(rich_text)

            # Write new text embedding to product column
            product.text_embedding = new_text_embedding.tolist()

            # Update PostgreSQL
            product.era = normalize_era(enrichment.get('era'), product_id=product.id)
            product.decade = enrichment.get('decade')
            if enrichment.get('culture'):
                product.culture = enrichment['culture']
            product.style_tags = json.dumps(enrichment.get('style_tags', []))
            product.colors = json.dumps(enrichment.get('colors', []))
            product.material = enrichment.get('material')
            product.pattern = enrichment.get('pattern')
            product.garment_type = enrichment.get('garment_type')
            product.vibe = enrichment.get('vibe')
            product.core_vibes = enrichment.get('core_vibes')
            product.bridge_vibes = enrichment.get('bridge_vibes')
            product.vibe_scores = enrichment.get('vibe_scores')
            product.fit_style = enrichment.get('fit_style')
            product.occasion = enrichment.get('occasion')
            product.ai_description = enrichment.get('ai_description')
            product.enriched_text = rich_text
            product.fp_category = enrichment.get('fp_category')
            product.nickname = enrichment.get('nickname')
            product.silhouette = enrichment.get('silhouette')
            product.neckline = enrichment.get('neckline')
            product.waistline = enrichment.get('waistline')
            product.length = enrichment.get('length')
            product.sleeve_length = enrichment.get('sleeve_length')
            product.opening_type = enrichment.get('opening_type')
            product.textile_pattern = enrichment.get('textile_pattern')
            product.textile_finishing = json.dumps(enrichment.get('textile_finishing', []))
            product.garment_parts = json.dumps(enrichment.get('garment_parts', []))
            product.decorations = json.dumps(enrichment.get('decorations', []))
            product.enriched_at = datetime.now()

            db.commit()

            success_count += 1
            print(f"  ✓ Era: {enrichment.get('era')} | Type: {enrichment.get('garment_type')}")

            # Rate limiting
            time.sleep(0.6)

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            failed_count += 1
            failed_items.append({
                'id': product.id,
                'platform': product.platform,
                'title': product.title,
                'category': product.category,
                'reason': str(e)[:100]
            })
            continue
        
        # Periodic summary every 100 items
        if i % 100 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60  # items per minute
            print(f"\n  --- PROGRESS: {i}/{len(products)} | "
                    f"{success_count} ok, {failed_count} failed, {non_garment_count} skipped | "
                    f"{rate:.1f} items/min ---")

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Successfully enriched:  {success_count}")
    print(f"  Non-garments (skipped): {non_garment_count}")
    print(f"  Failed (errors):        {failed_count}")

    if failed_items or non_garment_count > 0:
        print(f"\n{len(failed_items)} items could not be enriched:")
        for item in failed_items[:20]:
            print(f"  [{item['platform']}] {item['title'][:60]}")
            print(f"    Category: {item['category']} | Reason: {item['reason']}")
    report_unrecognized_eras()
    export_unrecognized_eras()

    db.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    limit = int(args[0]) if args else None
    enrich_remaining(limit=limit)
