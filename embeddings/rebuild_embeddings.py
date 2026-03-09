"""
Rebuild rich text and re-embed all products using stored enrichment data.
No Claude API calls — just reads from PostgreSQL and updates pgvector columns.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
import json


def rebuild_embeddings():
    print("\n" + "=" * 70)
    print("REBUILD EMBEDDINGS FROM STORED ENRICHMENT")
    print("No Claude API calls — just re-generating text + vectors")
    print("=" * 70)

    db = SessionLocal()
    generator = EmbeddingGenerator()
    enricher = ClaudeEnricher.__new__(ClaudeEnricher)  # skip API key init

    products = db.query(Product).filter(
        Product.enriched_at != None
    ).all()

    print(f"\nProducts to re-embed: {len(products)}")

    updated = 0

    for i, product in enumerate(products, 1):
        # Reconstruct enrichment dict from stored columns
        enrichment = {
            'era': product.era,
            'decade': product.decade,
            'style_tags': json.loads(product.style_tags) if product.style_tags else [],
            'colors': json.loads(product.colors) if product.colors else [],
            'material': product.material,
            'pattern': product.pattern,
            'garment_type': product.garment_type,
            'vibe': product.vibe,
            'fit_style': product.fit_style,
            'occasion': product.occasion,
            'season': product.season,
            'ai_description': product.ai_description,
        }

        product_data = {
            'title': product.title,
            'category': product.category,
        }

        # Rebuild rich text with the fixed build_rich_text method
        rich_text = enricher.build_rich_text(product_data, enrichment)

        # Generate new embedding
        new_embedding = generator.generate_text_embedding(rich_text)

        # Write new text embedding to product column
        product.text_embedding = new_embedding.tolist()

        # Update stored rich text in PostgreSQL
        product.enriched_text = rich_text
        db.commit()

        updated += 1
        if i % 25 == 0 or i == len(products):
            print(f"  [{i}/{len(products)}] re-embedded")

    print(f"\nDone! Re-embedded {updated} products.")
    print("Run test_enriched_search.py to check scores.")
    db.close()


if __name__ == '__main__':
    rebuild_embeddings()
