"""
Re-enrich Met Museum items with enhanced focus on extracting Fashionpedia taxonomy.

Met Museum items currently have creative fields (era, vibe) but missing structural
taxonomy (silhouette, neckline, etc.). This script forces re-enrichment with an
enhanced prompt that extracts taxonomy even from minimal descriptions.
"""
import sys
import os

# Add scripts directory to path so we can import modules
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, scripts_dir)

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
from datetime import datetime
import json
import time


def reenrich_met_museum(limit: int = None):
    """Re-enrich Met Museum items to extract Fashionpedia taxonomy."""

    print("\n" + "=" * 70)
    print("RE-ENRICHING MET MUSEUM ITEMS - TAXONOMY EXTRACTION")
    print("=" * 70)

    db = SessionLocal()
    enricher = ClaudeEnricher()
    generator = EmbeddingGenerator()

    # Get Met Museum items (even if previously enriched)
    query = db.query(Product).filter(Product.platform == 'met_museum')
    if limit:
        query = query.limit(limit)
    products = query.all()

    print(f"\nMet Museum products to re-enrich: {len(products)}")

    # Check current state
    with_taxonomy = sum(1 for p in products if p.fp_category or p.silhouette)
    without_taxonomy = len(products) - with_taxonomy

    print(f"  Already have taxonomy: {with_taxonomy}")
    print(f"  Missing taxonomy: {without_taxonomy}")
    print(f"\nEstimated cost: ${len(products) * 0.03:.2f}")
    print(f"Estimated time: ~{len(products) * 6 // 60} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return

    print("\n" + "=" * 70)
    print("Starting re-enrichment...")
    print("=" * 70)

    success_count = 0
    taxonomy_extracted_count = 0
    failed_count = 0

    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product.title[:60]}")

        try:
            # Force full enrichment (not creative-only)
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

            # Build rich text
            rich_text = enricher.build_rich_text(
                product_data={
                    'title': product.title,
                    'category': product.category
                },
                enrichment=enrichment
            )

            # Generate new text embedding
            new_text_embedding = generator.generate_text_embedding(rich_text)
            
            # Write new text embedding to product column
            product.text_embedding = new_text_embedding.tolist()

            # Update PostgreSQL
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
            # Fashionpedia taxonomy
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

            # Check if taxonomy was extracted
            has_taxonomy = (
                enrichment.get('fp_category') or
                enrichment.get('silhouette') or
                enrichment.get('waistline')
            )
            if has_taxonomy:
                taxonomy_extracted_count += 1
                print(f"  ✓ Taxonomy: {enrichment.get('fp_category')} | {enrichment.get('silhouette')}")
            else:
                print(f"  ⚠ No taxonomy extracted (item may not be a garment)")

            print(f"  Era: {enrichment.get('era')} ({enrichment.get('decade')})")

            # Rate limiting
            time.sleep(0.6)

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            failed_count += 1
            continue

    # Summary
    print("\n" + "=" * 70)
    print("RE-ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Successfully re-enriched: {success_count}")
    print(f"  With taxonomy extracted:  {taxonomy_extracted_count}")
    print(f"  Failed:                   {failed_count}")
    print(f"\nTaxonomy extraction rate: {taxonomy_extracted_count/success_count*100:.1f}%")

    db.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    limit = int(args[0]) if args else None
    reenrich_met_museum(limit=limit)
