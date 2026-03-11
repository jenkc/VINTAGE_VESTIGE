"""
Test search quality AFTER enrichment.
Compare against baseline results.
"""

from embeddings.generator import EmbeddingGenerator
from tools.migration.vector_db import VectorDB
from test_baseline_search import test_text_search_baseline


def test_enriched_search():
    """Test text search with enriched embeddings"""

    print("\n" + "=" * 70)
    print("ENRICHED SEARCH QUALITY TEST")
    print("Testing embeddings from CLAUDE-ENRICHED text")
    print("=" * 70)

    generator = EmbeddingGenerator()
    vector_db = VectorDB()

    # SAME queries as baseline - compare results!
    test_queries = [
        # Basic garment queries - should still match well
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

        # Modern vibe queries - enrichment should improve these!
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
            print(f"     Era: {result.get('era', 'N/A')}")

        top_score = results[0]['score'] if results else 0

        results_summary.append({
            'query': query,
            'expectation': expectation,
            'top_score': top_score,
            'top_result': results[0]['title'] if results else 'None',
            'era': results[0].get('era') if results else None
        })

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHED SEARCH SUMMARY")
    print("=" * 70)

    basic_queries = results_summary[:4]
    era_queries = results_summary[4:7]
    culture_queries = results_summary[7:10]
    vibe_queries = results_summary[10:]

    avg_basic = sum(r['top_score'] for r in basic_queries) / len(basic_queries)
    avg_era = sum(r['top_score'] for r in era_queries) / len(era_queries)
    avg_culture = sum(r['top_score'] for r in culture_queries) / len(culture_queries)
    avg_vibe = sum(r['top_score'] for r in vibe_queries) / len(vibe_queries)

    print("\nBASIC QUERIES (garment + material):")
    print(f"  Average score: {avg_basic:.3f}")

    print("\nERA QUERIES (1700s-1800s historical periods):")
    print(f"  Average score: {avg_era:.3f}")

    print("\nCULTURE QUERIES (French, British, American):")
    print(f"  Average score: {avg_culture:.3f}")

    print("\nMODERN VIBE QUERIES (BIG IMPROVEMENT EXPECTED):")
    print(f"  Average score: {avg_vibe:.3f}")

    overall = (avg_basic + avg_era + avg_culture + avg_vibe) / 4

    print(f"\nOVERALL ENRICHED: {overall:.3f}")

    return {
        'basic': avg_basic,
        'era': avg_era,
        'culture': avg_culture,
        'vibe': avg_vibe,
        'overall': overall,
        'details': results_summary
    }


def compare_with_baseline():
    """Run both tests and compare scores"""

    print("\n" + "=" * 70)
    print("RUNNING BASELINE vs ENRICHED COMPARISON")
    print("=" * 70)

    # Run baseline first
    print("\n>>> BASELINE (raw museum descriptions) <<<")
    baseline = test_text_search_baseline()

    # Run enriched
    print("\n>>> ENRICHED (Claude-enhanced text) <<<")
    enriched = test_enriched_search()

    # Compare
    print("\n" + "=" * 70)
    print("COMPARISON: BASELINE vs ENRICHED")
    print("=" * 70)

    categories = ['basic', 'era', 'culture', 'vibe']
    labels = [
        'BASIC (garment + material)',
        'ERA (1700s-1800s periods)',
        'CULTURE (French, British, American)',
        'MODERN VIBE (style language)'
    ]

    for cat, label in zip(categories, labels):
        b = baseline[cat]
        e = enriched[cat]
        diff = e - b
        pct = (diff / b * 100) if b > 0 else 0
        print(f"\n{label}:")
        print(f"  Baseline: {b:.3f}  ->  Enriched: {e:.3f}  ({diff:+.3f}, {pct:+.1f}%)")

    b_overall = baseline['overall']
    e_overall = enriched['overall']
    diff = e_overall - b_overall
    pct = (diff / b_overall * 100) if b_overall > 0 else 0

    print(f"\nOVERALL:")
    print(f"  Baseline: {b_overall:.3f}  ->  Enriched: {e_overall:.3f}  ({diff:+.3f}, {pct:+.1f}%)")

    if e_overall >= 0.75:
        print("\nSUCCESS! Search quality meets production standards!")
    elif e_overall >= 0.65:
        print("\nGood improvement, but room for optimization")
    else:
        print("\nNeeds more work - check enrichment quality")


if __name__ == '__main__':
    import sys

    if '--compare' in sys.argv:
        compare_with_baseline()
    else:
        test_enriched_search()
