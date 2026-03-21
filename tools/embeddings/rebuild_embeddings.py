"""
Rebuild rich text and re-embed all products using stored enrichment data.
No Claude API calls — just reads from PostgreSQL and updates pgvector columns.
"""
import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher
import json

BATCH_SIZE = 500

# all-mpnet-base-v2 max sequence length in tokens (~words * 1.3)
MAX_TOKEN_ESTIMATE = 384
WORD_TO_TOKEN_RATIO = 1.3


def rebuild_embeddings():
    print("\n" + "=" * 70)
    print("REBUILD EMBEDDINGS FROM STORED ENRICHMENT")
    print("No Claude API calls — just re-generating text + vectors")
    print("=" * 70)

    db = SessionLocal()
    generator = EmbeddingGenerator()

    total = db.query(Product).filter(Product.enriched_at != None).count()
    print(f"\nProducts to re-embed: {total}")

    updated = 0
    failed = 0
    truncated = 0
    processed = 0
    start = time.time()

    offset = 0
    while offset < total:
        products = (
            db.query(Product)
            .filter(Product.enriched_at != None)
            .order_by(Product.id)
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )
        if not products:
            break

        for product in products:
            processed += 1
            try:
                enrichment = {
                    'ai_description': product.ai_description,
                    'era': product.era,
                    'decade': product.decade,
                    'garment_type': product.garment_type,
                    'nickname': product.nickname,
                    'material': product.material,
                    'colors': json.loads(product.colors) if product.colors else [],
                    'style_tags': json.loads(product.style_tags) if product.style_tags else [],
                    'vibe_scores': product.vibe_scores,
                    'silhouette': product.silhouette,
                    'neckline': product.neckline,
                    'length': product.length,
                    'waistline': product.waistline,
                    'sleeve_length': product.sleeve_length,
                    'fit_style': product.fit_style,
                    'textile_pattern': product.textile_pattern,
                    'textile_finishing': product.textile_finishing,
                    'occasion': product.occasion,
                    'decorations': product.decorations,
                    'construction_technique': product.construction_technique,
                    'social_function': product.social_function,
                    'motif_family': product.motif_family,
                    'designer': product.designer,
                    'influence_references': product.influence_references,
                    'named_movements': product.named_movements,
                    'display_title': product.display_title,
                }

                product_data = {
                    'title': product.title,
                    'category': product.category,
                }

                rich_text = ClaudeEnricher.build_rich_text(product_data, enrichment)

                word_count = len(rich_text.split())
                est_tokens = int(word_count * WORD_TO_TOKEN_RATIO)
                if est_tokens > MAX_TOKEN_ESTIMATE:
                    truncated += 1

                new_embedding = generator.generate_text_embedding(rich_text)

                product.text_embedding = new_embedding.tolist()
                product.enriched_text = rich_text
                updated += 1

            except Exception as e:
                print(f"  ERR [{product.id}] {product.title[:40]}: {e}")
                failed += 1

        db.commit()
        offset += BATCH_SIZE

        elapsed = time.time() - start
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / rate if rate > 0 else 0
        print(f"  [{processed}/{total}]  {rate:.1f}/s  ETA {eta:.0f}s  "
              f"({updated} ok, {failed} err, {truncated} truncated)")
    elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print(f"REBUILD COMPLETE in {elapsed:.0f}s")
    print(f"{'=' * 70}")
    print(f"  Updated:   {updated}")
    print(f"  Failed:    {failed}")
    print(f"  Truncated: {truncated} (exceeded ~{MAX_TOKEN_ESTIMATE} token estimate)")
    if truncated > 0:
        print(f"  Note: truncated texts still get embedded — the model clips the tail.")
        print(f"  KG fields (designer, influences, movements) may be partially lost.")
    print(f"\n  Next: venv/bin/python tools/analysis/compute_bridges.py --rebuild")

    db.close()


if __name__ == '__main__':
    rebuild_embeddings()
