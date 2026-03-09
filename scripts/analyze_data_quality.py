"""
Data Quality Analysis — Post-Enrichment Report

Generates a comprehensive quality report after enrichment runs.
Covers completeness, distributions, field sparsity, and flags outliers.

Usage:
  venv/bin/python scripts/analyze_data_quality.py
  venv/bin/python scripts/analyze_data_quality.py --csv   # also export CSVs
"""
import sys
import os
import json
import csv
from collections import Counter

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from storage.database import SessionLocal, Product, StyleBridge
from sqlalchemy import text, func, distinct


def section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def run_report(export_csv=False):
    db = SessionLocal()

    # =========================================================================
    # 1. OVERVIEW
    # =========================================================================
    section("1. OVERVIEW")

    total = db.query(Product).count()
    enriched = db.query(Product).filter(Product.enriched_at != None).count()
    unenriched = total - enriched
    has_text_emb = db.execute(
        text("SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL")
    ).scalar()
    has_image_emb = db.execute(
        text("SELECT COUNT(*) FROM products WHERE image_embedding IS NOT NULL")
    ).scalar()
    bridge_count = db.query(StyleBridge).count()
    has_narrative = db.query(StyleBridge).filter(
        StyleBridge.bridge_narrative != None
    ).count()

    print(f"  Total products:       {total}")
    print(f"  Enriched:             {enriched} ({enriched/total*100:.1f}%)")
    print(f"  Unenriched:           {unenriched}")
    print(f"  Text embeddings:      {has_text_emb}")
    print(f"  Image embeddings:     {has_image_emb}")
    print(f"  Style bridges:        {bridge_count}")
    print(f"  Bridge narratives:    {has_narrative}/{bridge_count}")

    # =========================================================================
    # 2. PLATFORM BREAKDOWN
    # =========================================================================
    section("2. PLATFORM BREAKDOWN")

    platforms = db.query(
        Product.platform,
        func.count(Product.id),
        func.count(Product.enriched_at),
    ).group_by(Product.platform).all()

    print(f"  {'Platform':<20} {'Total':>6} {'Enriched':>9} {'%':>6}")
    print(f"  {'-'*20} {'-'*6} {'-'*9} {'-'*6}")
    for platform, count, enr_count in sorted(platforms, key=lambda x: x[1], reverse=True):
        pct = enr_count / count * 100 if count else 0
        print(f"  {platform:<20} {count:>6} {enr_count:>9} {pct:>5.1f}%")

    # =========================================================================
    # 3. FIELD SPARSITY (enriched products only)
    # =========================================================================
    section("3. FIELD SPARSITY (enriched products only)")

    fields_to_check = [
        'era', 'decade', 'fp_category', 'garment_type', 'material',
        'silhouette', 'neckline', 'waistline', 'length', 'sleeve_length',
        'opening_type', 'textile_pattern', 'ai_description', 'enriched_text',
        'fit_style', 'occasion', 'culture',
    ]

    array_fields = ['core_vibes', 'bridge_vibes']
    json_fields_check = ['vibe_scores']
    json_list_fields = ['style_tags', 'colors', 'textile_finishing', 'garment_parts', 'decorations']

    print(f"\n  {'Field':<22} {'Filled':>7} {'Empty':>7} {'Fill %':>7}")
    print(f"  {'-'*22} {'-'*7} {'-'*7} {'-'*7}")

    for field in fields_to_check:
        filled = db.query(Product).filter(
            Product.enriched_at != None,
            getattr(Product, field) != None,
            getattr(Product, field) != '',
        ).count()
        empty = enriched - filled
        pct = filled / enriched * 100 if enriched else 0
        flag = " <-- SPARSE" if pct < 50 else ""
        print(f"  {field:<22} {filled:>7} {empty:>7} {pct:>6.1f}%{flag}")

    # Array fields (ARRAY type)
    for field in array_fields:
        filled = db.execute(text(f"""
            SELECT COUNT(*) FROM products
            WHERE enriched_at IS NOT NULL
            AND {field} IS NOT NULL
            AND array_length({field}, 1) > 0
        """)).scalar()
        empty = enriched - filled
        pct = filled / enriched * 100 if enriched else 0
        flag = " <-- SPARSE" if pct < 50 else ""
        print(f"  {field:<22} {filled:>7} {empty:>7} {pct:>6.1f}%{flag}")

    # JSON dict fields
    for field in json_fields_check:
        filled = db.query(Product).filter(
            Product.enriched_at != None,
            getattr(Product, field) != None,
        ).count()
        empty = enriched - filled
        pct = filled / enriched * 100 if enriched else 0
        flag = " <-- SPARSE" if pct < 50 else ""
        print(f"  {field:<22} {filled:>7} {empty:>7} {pct:>6.1f}%{flag}")

    # JSON list fields (stored as Text, need to parse)
    for field in json_list_fields:
        filled = db.execute(text(f"""
            SELECT COUNT(*) FROM products
            WHERE enriched_at IS NOT NULL
            AND {field} IS NOT NULL
            AND {field} != '[]'
            AND {field} != ''
        """)).scalar()
        empty = enriched - filled
        pct = filled / enriched * 100 if enriched else 0
        flag = " <-- SPARSE" if pct < 50 else ""
        print(f"  {field:<22} {filled:>7} {empty:>7} {pct:>6.1f}%{flag}")

    # =========================================================================
    # 4. ERA DISTRIBUTION
    # =========================================================================
    section("4. ERA DISTRIBUTION")

    eras = db.query(
        Product.era,
        func.count(Product.id),
    ).filter(
        Product.enriched_at != None,
    ).group_by(Product.era).order_by(func.count(Product.id).desc()).all()

    print(f"  {'Era':<40} {'Count':>6}")
    print(f"  {'-'*40} {'-'*6}")
    for era, count in eras:
        era_label = era if era else '(NULL)'
        print(f"  {era_label:<40} {count:>6}")

    # =========================================================================
    # 5. PLATFORM x ERA HEATMAP
    # =========================================================================
    section("5. PLATFORM x ERA (top 15 eras)")

    top_eras = [e[0] for e in eras[:15] if e[0]]

    cross = db.query(
        Product.platform,
        Product.era,
        func.count(Product.id),
    ).filter(
        Product.enriched_at != None,
        Product.era.in_(top_eras),
    ).group_by(Product.platform, Product.era).all()

    # Build matrix
    platform_names = sorted(set(r[0] for r in cross))
    matrix = {}
    for plat, era, cnt in cross:
        matrix.setdefault(era, {})[plat] = cnt

    header = f"  {'Era':<35}" + "".join(f"{p:>14}" for p in platform_names)
    print(header)
    print(f"  {'-'*35}" + "".join(f"{'-'*14}" for _ in platform_names))
    for era in top_eras:
        row = f"  {era:<35}"
        for plat in platform_names:
            val = matrix.get(era, {}).get(plat, 0)
            row += f"{val:>14}" if val else f"{'·':>14}"

        print(row)

    # =========================================================================
    # 6. CORE VIBES DISTRIBUTION
    # =========================================================================
    section("6. CORE VIBES DISTRIBUTION")

    vibe_rows = db.execute(text("""
        SELECT core_vibes FROM products
        WHERE enriched_at IS NOT NULL
        AND core_vibes IS NOT NULL
        AND array_length(core_vibes, 1) > 0
    """)).fetchall()

    vibe_counter = Counter()
    for (vibes,) in vibe_rows:
        for v in vibes:
            vibe_counter[v] += 1

    print(f"  Products with core_vibes: {len(vibe_rows)}")
    print(f"  Unique vibe terms: {len(vibe_counter)}\n")
    print(f"  {'Vibe Term':<35} {'Count':>6} {'%':>6}")
    print(f"  {'-'*35} {'-'*6} {'-'*6}")
    for vibe, count in vibe_counter.most_common():
        pct = count / len(vibe_rows) * 100
        print(f"  {vibe:<35} {count:>6} {pct:>5.1f}%")

    # =========================================================================
    # 7. BRIDGE VIBES DISTRIBUTION
    # =========================================================================
    section("7. BRIDGE VIBES DISTRIBUTION")

    bvibe_rows = db.execute(text("""
        SELECT bridge_vibes FROM products
        WHERE enriched_at IS NOT NULL
        AND bridge_vibes IS NOT NULL
        AND array_length(bridge_vibes, 1) > 0
    """)).fetchall()

    bvibe_counter = Counter()
    for (vibes,) in bvibe_rows:
        for v in vibes:
            bvibe_counter[v] += 1

    print(f"  Products with bridge_vibes: {len(bvibe_rows)}")
    print(f"  Unique bridge vibe terms: {len(bvibe_counter)}\n")
    print(f"  {'Bridge Vibe Term':<35} {'Count':>6} {'%':>6}")
    print(f"  {'-'*35} {'-'*6} {'-'*6}")
    for vibe, count in bvibe_counter.most_common():
        pct = count / len(bvibe_rows) * 100
        print(f"  {vibe:<35} {count:>6} {pct:>5.1f}%")

    # =========================================================================
    # 8. FP_CATEGORY DISTRIBUTION
    # =========================================================================
    section("8. FP_CATEGORY DISTRIBUTION")

    cats = db.query(
        Product.fp_category,
        func.count(Product.id),
    ).filter(
        Product.enriched_at != None,
    ).group_by(Product.fp_category).order_by(func.count(Product.id).desc()).all()

    print(f"  {'Category':<30} {'Count':>6}")
    print(f"  {'-'*30} {'-'*6}")
    for cat, count in cats:
        cat_label = cat if cat else '(NULL)'
        print(f"  {cat_label:<30} {count:>6}")

    # =========================================================================
    # 9. GARMENT TYPE DISTRIBUTION
    # =========================================================================
    section("9. GARMENT TYPE DISTRIBUTION (top 25)")

    gtypes = db.query(
        Product.garment_type,
        func.count(Product.id),
    ).filter(
        Product.enriched_at != None,
    ).group_by(Product.garment_type).order_by(func.count(Product.id).desc()).limit(25).all()

    print(f"  {'Garment Type':<35} {'Count':>6}")
    print(f"  {'-'*35} {'-'*6}")
    for gt, count in gtypes:
        gt_label = gt if gt else '(NULL)'
        print(f"  {gt_label:<35} {count:>6}")

    # =========================================================================
    # 10. OUTLIER DETECTION
    # =========================================================================
    section("10. POTENTIAL OUTLIERS")

    # Enriched but missing era
    no_era = db.query(Product).filter(
        Product.enriched_at != None,
        (Product.era == None) | (Product.era == ''),
    ).limit(10).all()
    print(f"\n  Enriched but no era ({len(no_era)} shown, may be more):")
    for p in no_era:
        print(f"    [{p.platform}] id={p.id} {p.title[:55]}")

    # Enriched but missing fp_category
    no_cat = db.query(Product).filter(
        Product.enriched_at != None,
        Product.fp_category == None,
    ).limit(10).all()
    print(f"\n  Enriched but no fp_category ({len(no_cat)} shown):")
    for p in no_cat:
        print(f"    [{p.platform}] id={p.id} {p.title[:55]}")

    # Enriched but missing core_vibes
    no_vibes = db.execute(text("""
        SELECT id, platform, LEFT(title, 55) as title FROM products
        WHERE enriched_at IS NOT NULL
        AND (core_vibes IS NULL OR array_length(core_vibes, 1) IS NULL)
        LIMIT 10
    """)).fetchall()
    print(f"\n  Enriched but no core_vibes ({len(no_vibes)} shown):")
    for row in no_vibes:
        print(f"    [{row[1]}] id={row[0]} {row[2]}")

    # Non-canonical era values (not in taxonomy)
    from enrichment.era_taxonomy import ERAS
    canonical_eras = set(ERAS.keys())
    era_values = db.query(distinct(Product.era)).filter(
        Product.enriched_at != None,
        Product.era != None,
    ).all()
    non_canonical = [e[0] for e in era_values if e[0] not in canonical_eras]
    print(f"\n  Non-canonical era values ({len(non_canonical)}):")
    for era in sorted(non_canonical):
        count = db.query(Product).filter(Product.era == era).count()
        print(f"    '{era}' ({count} products)")

    # Off-vocabulary vibes
    from enrichment.claude import VIBE_VOCABULARY
    # Extract valid terms from VIBE_VOCABULARY string
    valid_vibes = set()
    for line in VIBE_VOCABULARY.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            # Extract term before any colon or parenthetical
            term = line[2:].split(':')[0].split('(')[0].strip()
            if term:
                valid_vibes.add(term)

    if valid_vibes:
        off_vocab = set(vibe_counter.keys()) - valid_vibes
        if off_vocab:
            print(f"\n  Off-vocabulary core_vibes ({len(off_vocab)}):")
            for v in sorted(off_vocab):
                print(f"    '{v}' ({vibe_counter[v]} products)")
        else:
            print(f"\n  All core_vibes are on-vocabulary.")

    # =========================================================================
    # 11. BRIDGE STATS (if bridges exist)
    # =========================================================================
    if bridge_count > 0:
        section("11. BRIDGE STATISTICS")

        type_stats = db.query(
            StyleBridge.bridge_type,
            func.count(StyleBridge.id),
            func.avg(StyleBridge.text_similarity),
            func.min(StyleBridge.text_similarity),
            func.max(StyleBridge.text_similarity),
        ).group_by(StyleBridge.bridge_type).all()

        print(f"  {'Type':<20} {'Count':>7} {'Avg':>7} {'Min':>7} {'Max':>7}")
        print(f"  {'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
        for btype, cnt, avg, mn, mx in sorted(type_stats, key=lambda x: x[1], reverse=True):
            btype_label = btype if btype else '(NULL)'
            print(f"  {btype_label:<20} {cnt:>7} {avg:>7.3f} {mn:>7.3f} {mx:>7.3f}")

        # Cross-platform bridge percentage
        cross_plat = db.execute(text("""
            SELECT COUNT(*) FROM style_bridges sb
            JOIN products p1 ON sb.source_id = p1.id
            JOIN products p2 ON sb.target_id = p2.id
            WHERE p1.platform != p2.platform
        """)).scalar()
        print(f"\n  Cross-platform bridges: {cross_plat}/{bridge_count} ({cross_plat/bridge_count*100:.1f}%)")

    # =========================================================================
    # CSV EXPORT
    # =========================================================================
    if export_csv:
        section("EXPORTING CSVs")

        # Era distribution
        with open('data_quality_eras.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['era', 'count'])
            for era, count in eras:
                w.writerow([era or '(NULL)', count])
        print(f"  Wrote data_quality_eras.csv")

        # Vibe distribution
        with open('data_quality_vibes.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['vibe', 'count', 'pct'])
            for vibe, count in vibe_counter.most_common():
                w.writerow([vibe, count, f"{count/len(vibe_rows)*100:.1f}"])
        print(f"  Wrote data_quality_vibes.csv")

        # Platform x Era
        with open('data_quality_platform_era.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['era'] + platform_names)
            for era in top_eras:
                row = [era] + [matrix.get(era, {}).get(p, 0) for p in platform_names]
                w.writerow(row)
        print(f"  Wrote data_quality_platform_era.csv")

        # fp_category distribution
        with open('data_quality_categories.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['fp_category', 'count'])
            for cat, count in cats:
                w.writerow([cat or '(NULL)', count])
        print(f"  Wrote data_quality_categories.csv")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    section("SUMMARY")

    issues = []
    if unenriched > 0:
        issues.append(f"{unenriched} products not yet enriched")
    if has_text_emb < enriched:
        issues.append(f"{enriched - has_text_emb} enriched products missing text embeddings")
    if len(non_canonical) > 0:
        issues.append(f"{len(non_canonical)} non-canonical era values need aliases")
    if len(no_vibes) > 0:
        issues.append(f"Some enriched products missing core_vibes")
    if bridge_count > 0 and has_narrative < bridge_count:
        issues.append(f"{bridge_count - has_narrative} bridges missing narratives")

    if issues:
        print(f"  {len(issues)} issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
    else:
        print(f"  No issues found. Dataset looks clean.")

    db.close()
    print()


if __name__ == '__main__':
    export = '--csv' in sys.argv
    run_report(export_csv=export)
