"""
Test search quality BEFORE Claude enrichment.
This establishes baseline performance with Met Museum data.
"""

from embeddings.generator import EmbeddingGenerator
from scripts.vector_db import VectorDB
from storage.database import SessionLocal, Product
from typing import List, Dict
import base64
from io import BytesIO
from PIL import Image


def test_text_search_baseline():
    """Test text search with raw Met Museum descriptions"""

    print("\n" + "=" * 70)
    print("BASELINE TEXT SEARCH QUALITY TEST")
    print("Testing embeddings from RAW Met Museum descriptions")
    print("=" * 70)

    generator = EmbeddingGenerator()
    vector_db = VectorDB()

    test_queries = [
        # Basic garment queries - items that exist in the collection
        ("silk evening dress", "Should find evening dresses"),
        ("wool coat or cape", "Should find outerwear"),
        ("lace bonnet", "Should find bonnets/headwear"),
        ("embroidered waistcoat", "Should find waistcoats"),

        # Era queries - 1700s and 1800s dominate the collection
        ("18th century robe", "Should find 1700s robes/gowns"),
        ("1800s Victorian dress", "Should find 19th century items"),
        ("Georgian era fashion", "Should find 1700s-1800s items"),

        # Culture queries - French, British, American are well represented
        ("French silk gown", "Should find French items"),
        ("British corset or stays", "Should find British items"),
        ("American formal wear", "Should find American items"),

        # Modern style language - baseline should struggle here
        ("dark academia aesthetic", "Modern vibe - enrichment target"),
        ("cottagecore pastoral dress", "Modern vibe - enrichment target"),
        ("romantic gothic fashion", "Modern vibe - enrichment target"),
        ("old money elegance", "Modern vibe - enrichment target"),
    ]

    results_summary = []

    for query, expectation in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"  Expected: {expectation}")
        print("  " + "-" * 60)

        query_embedding = generator.generate_text_embedding(query)

        results = vector_db.search_similar(
            collection='vintage_text',
            query_vector=query_embedding,
            limit=3
        )

        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']}")
            print(f"     Score: {result['score']:.3f}")

        top_score = results[0]['score'] if results else 0

        results_summary.append({
            'query': query,
            'expectation': expectation,
            'top_score': top_score,
            'top_result': results[0]['title'] if results else 'None'
        })

    # Summary
    print("\n" + "=" * 70)
    print("BASELINE SUMMARY")
    print("=" * 70)

    basic_queries = results_summary[:4]
    era_queries = results_summary[4:7]
    culture_queries = results_summary[7:10]
    vibe_queries = results_summary[10:]

    print("\nBASIC QUERIES (garment + material):")
    avg_basic = sum(r['top_score'] for r in basic_queries) / len(basic_queries)
    print(f"  Average score: {avg_basic:.3f}")

    print("\nERA QUERIES (1700s-1800s historical periods):")
    avg_era = sum(r['top_score'] for r in era_queries) / len(era_queries)
    print(f"  Average score: {avg_era:.3f}")

    print("\nCULTURE QUERIES (French, British, American):")
    avg_culture = sum(r['top_score'] for r in culture_queries) / len(culture_queries)
    print(f"  Average score: {avg_culture:.3f}")

    print("\nMODERN VIBE QUERIES (style language - enrichment target):")
    avg_vibe = sum(r['top_score'] for r in vibe_queries) / len(vibe_queries)
    print(f"  Average score: {avg_vibe:.3f}")

    overall = (avg_basic + avg_era + avg_culture + avg_vibe) / 4
    print(f"\nOVERALL BASELINE: {overall:.3f}")

    return {
        'basic': avg_basic,
        'era': avg_era,
        'culture': avg_culture,
        'vibe': avg_vibe,
        'overall': overall,
        'details': results_summary
    }


def test_image_search():
    """Test image search (CLIP - doesn't change with enrichment)"""

    print("\n" + "=" * 70)
    print("IMAGE SIMILARITY SEARCH TEST")
    print("=" * 70)

    db = SessionLocal()
    generator = EmbeddingGenerator()
    vector_db = VectorDB()

    source = db.query(Product).filter(Product.primary_image != None).first()

    print(f"\nSource Product:")
    print(f"  {source.title}")
    print(f"  Category: {source.category}")

    if source.primary_image and source.primary_image.startswith('data:image'):
        header, encoded = source.primary_image.split(',', 1)
        image_data = base64.b64decode(encoded)
        source_image = Image.open(BytesIO(image_data))

        image_vector = generator.generate_image_embedding(source_image)

        results = vector_db.search_similar(
            collection='vintage_images',
            query_vector=image_vector,
            limit=6
        )[1:]  # Skip source itself

        print("\nVisually Similar Products:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']}")
            print(f"     Score: {result['score']:.3f}")

        print("\nImage search works! (Won't change with enrichment)")

    db.close()


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("BASELINE SEARCH QUALITY TEST")
    print("Testing performance BEFORE Claude enrichment")
    print("=" * 70)

    results = test_text_search_baseline()
    test_image_search()

    print("\n" + "=" * 70)
    print("BASELINE TEST COMPLETE")
    print("=" * 70)
    print("\nNext: Enrichment will improve modern vibe queries significantly!")
