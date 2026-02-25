"""
Rebuild rich text and re-embed all products using stored enrichment data.
No Claude API calls — just reads from PostgreSQL and updates Qdrant.
"""

from storage.database import SessionLocal, Product
from storage.vector_db import VectorDB
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
from qdrant_client.models import PointStruct
import json


def rebuild_embeddings():
    print("\n" + "=" * 70)
    print("REBUILD EMBEDDINGS FROM STORED ENRICHMENT")
    print("No Claude API calls — just re-generating text + vectors")
    print("=" * 70)

    db = SessionLocal()
    generator = EmbeddingGenerator()
    vector_db = VectorDB()
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

        # Update Qdrant
        vector_db.client.upsert(
            collection_name='vintage_text',
            points=[PointStruct(
                id=product.id,
                vector=new_embedding.tolist(),
                payload={
                    'product_id': product.id,
                    'title': product.title,
                    'category': product.category,
                    'era': product.era,
                    'decade': product.decade,
                    'style_tags': enrichment['style_tags'],
                    'colors': enrichment['colors'],
                    'material': product.material,
                    'pattern': product.pattern,
                    'garment_type': product.garment_type,
                    'vibe': product.vibe,
                    'fit_style': product.fit_style,
                    'occasion': product.occasion,
                    'ai_description': product.ai_description,
                    'season': product.season,
                    'price': product.price,
                    'primary_image': product.primary_image,
                    'culture': product.culture,
                    'object_date': product.object_date,
                }
            )]
        )

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
