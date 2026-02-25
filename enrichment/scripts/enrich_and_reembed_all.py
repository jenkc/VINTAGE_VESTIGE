"""
Complete enrichment pipeline:
1. Get products from database
2. Enrich each with Claude
3. Build rich text from enrichment
4. Generate NEW text embeddings from rich text
5. Update Qdrant with new embeddings
6. Store enrichment metadata in PostgreSQL
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product
from storage.vector_db import VectorDB
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
from qdrant_client.models import PointStruct
from datetime import datetime


def enrich_and_reembed_all(limit: int = None):
    """
    Main enrichment pipeline.
    Replaces baseline embeddings with enriched embeddings.
    """

    print("\n" + "=" * 70)
    print("VINTAGE VESTIGE - ENRICHMENT + RE-EMBEDDING PIPELINE")
    print("=" * 70)

    db = SessionLocal()
    enricher = ClaudeEnricher()
    generator = EmbeddingGenerator()
    vector_db = VectorDB()

    # Get products (prioritize un-enriched)
    products = db.query(Product).filter(
        Product.enriched_at == None
    ).limit(limit).all()

    if not products:
        print("All products already enriched! Use --force to re-enrich.")
        products = db.query(Product).limit(limit).all()

    # Count by type for cost estimate
    fp_count = sum(1 for p in products if p.platform == 'fashionpedia' and p.fp_category)
    full_count = len(products) - fp_count
    est_cost = full_count * 0.03 + fp_count * 0.015  # creative-only is cheaper

    print(f"\nProducts to enrich: {len(products)}")
    print(f"  Full enrichment: {full_count}")
    print(f"  Creative-only (Fashionpedia): {fp_count}")
    print(f"Estimated cost: ${est_cost:.2f}")
    print(f"Estimated time: ~{len(products) * 5 // 60} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return
    else:
        print("\n  [auto-confirmed with --yes]")

    print("\n" + "=" * 70)
    print("Starting enrichment pipeline...")
    print("=" * 70)

    enriched_count = 0
    failed_count = 0

    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product.title}")

        try:
            # Step 1: Claude enrichment
            # Use creative-only path for items with expert annotations (e.g. Fashionpedia)
            has_expert_annotations = (
                product.platform == 'fashionpedia' and product.fp_category is not None
            )

            if has_expert_annotations:
                # Gather existing structured fields
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
                print(f"  [creative-only enrichment]")
            else:
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

            # Step 2: Build rich text
            rich_text = enricher.build_rich_text(
                product_data={
                    'title': product.title,
                    'category': product.category
                },
                enrichment=enrichment
            )

            print(f"  Rich text: {rich_text[:80]}...")

            # Step 3: Generate NEW text embedding from rich text
            new_text_embedding = generator.generate_text_embedding(rich_text)

            # Step 4: Update Qdrant (REPLACE old embedding)
            vector_db.client.upsert(
                collection_name='vintage_text',
                points=[PointStruct(
                    id=product.id,
                    vector=new_text_embedding.tolist(),
                    payload={
                        'product_id': product.id,
                        'title': product.title,
                        'category': product.category,
                        'era': enrichment.get('era'),
                        'decade': enrichment.get('decade'),
                        'style_tags': enrichment.get('style_tags', []),
                        'colors': enrichment.get('colors', []),
                        'material': enrichment.get('material'),
                        'garment_type': enrichment.get('garment_type'),
                        'vibe': enrichment.get('vibe'),
                        'fit_style': enrichment.get('fit_style'),
                        'occasion': enrichment.get('occasion'),
                        'ai_description': enrichment.get('ai_description'),
                        'season': enrichment.get('season'),
                        'price': product.price,
                        'primary_image': product.primary_image,
                        'culture': product.culture,
                        'object_date': product.object_date,
                        # Fashionpedia taxonomy
                        'fp_category': enrichment.get('fp_category'),
                        'nickname': enrichment.get('nickname'),
                        'silhouette': enrichment.get('silhouette'),
                        'neckline': enrichment.get('neckline'),
                        'waistline': enrichment.get('waistline'),
                        'length': enrichment.get('length'),
                        'sleeve_length': enrichment.get('sleeve_length'),
                        'opening_type': enrichment.get('opening_type'),
                        'textile_pattern': enrichment.get('textile_pattern'),
                        'textile_finishing': enrichment.get('textile_finishing', []),
                        'garment_parts': enrichment.get('garment_parts', []),
                        'decorations': enrichment.get('decorations', []),
                    }
                )]
            )

            # Step 5: Store enrichment in PostgreSQL
            product.era = enrichment.get('era')
            product.decade = enrichment.get('decade')
            product.style_tags = json.dumps(enrichment.get('style_tags', []))
            product.colors = json.dumps(enrichment.get('colors', []))
            product.material = enrichment.get('material')
            product.pattern = enrichment.get('pattern')
            product.garment_type = enrichment.get('garment_type')
            product.vibe = enrichment.get('vibe')
            product.fit_style = enrichment.get('fit_style')
            product.occasion = enrichment.get('occasion')
            product.ai_description = enrichment.get('ai_description')
            product.enriched_text = rich_text
            # Fashionpedia taxonomy fields
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

            enriched_count += 1
            tags = enrichment.get('style_tags', [])[:2]
            print(f"  {enrichment.get('era')} ({enrichment.get('decade')}) | Style: {', '.join(tags)}")

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
            failed_count += 1
            continue

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Successfully enriched: {enriched_count}")
    print(f"  Failed: {failed_count}")
    print(f"\nNext: Run test_enriched_search.py to measure improvement!")

    db.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    limit = int(args[0]) if args else None
    enrich_and_reembed_all(limit=limit)
