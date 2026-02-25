"""
Compute style bridges between all products.

Three bridge passes per product:
  1. Open discovery — strongest connections regardless of source
  2. Cross-category — similar structure, different garment type
  3. Cross-vibe — similar structure, different aesthetic

Date-first temporal classification with platform fallback.

Bridge score formula:
  With images:    0.40 * text_sim + 0.30 * image_sim + 0.30 * structural
  Without images: 0.55 * text_sim + 0.45 * structural

Bridge types:
  cross_era:       items >30 years apart (date-first, platform fallback)
  near_era:        items 10-30 years apart
  same_era:        items <10 years apart
  cross_category:  different fp_category, shared structural DNA
  cross_vibe:      different aesthetic vibe, shared structural DNA

Usage:
  python analysis/compute_bridges.py [--rebuild] [--limit=N]

Run from project root.
"""

import sys
import os
import json
import re
import time
from datetime import datetime

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product, StyleBridge
from storage.vector_db import VectorDB
from qdrant_client.models import Filter, FieldCondition, MatchValue, HasIdCondition
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HISTORICAL_PLATFORMS = {'met_museum', 'smithsonian'}
MODERN_PLATFORMS = {'fashionpedia'}

# Temporal classification thresholds (years)
CROSS_ERA_DISTANCE = 30
NEAR_ERA_DISTANCE = 10

# Structural field weights (from cross_source_bridges.md)
STRUCTURAL_WEIGHTS = {
    'fp_category':       0.20,
    'silhouette':        0.15,
    'nickname':          0.10,
    'neckline':          0.10,
    'length':            0.10,
    'waistline':         0.08,
    'sleeve_length':     0.07,
    'textile_pattern':   0.05,
    'opening_type':      0.05,
    'garment_parts':     0.05,   # Jaccard
    'decorations':       0.03,   # Jaccard
    'textile_finishing': 0.02,   # Jaccard
}

SET_FIELDS = {'garment_parts', 'decorations', 'textile_finishing'}

# Era -> approximate year (fallback when no explicit date)
ERA_YEAR_MAP = {
    'medieval':           1300,
    'renaissance':        1500,
    'baroque':            1650,
    'rococo':             1750,
    'georgian':           1770,
    'regency':            1815,
    'romantic':           1835,
    'victorian':          1870,
    'edwardian':          1905,
    'art nouveau':        1900,
    'art deco':           1925,
    'mid-century modern': 1955,
    'mid-century':        1955,
    'mod':                1965,
    'disco':              1975,
    'new wave':           1982,
    'grunge':             1993,
    'y2k':                2000,
    'contemporary':       2015,
    'modern':             2015,
}


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

def extract_approximate_year(product) -> int | None:
    """
    Extract an approximate year from product fields.
    Tries in order: year -> decade -> object_date -> era.
    """
    # 1. Direct year field
    if product.year and product.year > 0:
        return int(product.year)

    # 2. Decade ("1870s" -> 1875)
    if product.decade:
        m = re.match(r'(\d{4})s', product.decade)
        if m:
            return int(m.group(1)) + 5

    # 3. object_date freeform parsing
    if product.object_date:
        od = product.object_date

        # "1860-1870" or "1860--1870" -> midpoint
        m = re.search(r'(\d{4})\s*[-\u2013]+\s*(\d{4})', od)
        if m:
            return (int(m.group(1)) + int(m.group(2))) // 2

        # "ca. 1865", "c. 1865", "circa 1865", or bare "1865"
        m = re.search(r'(?:ca?\.?\s*|circa\s+)?(\d{4})', od)
        if m:
            return int(m.group(1))

        # "early/mid/late 19th century"
        m = re.search(
            r'(early|mid|late)\s+(\d{1,2})(?:th|st|nd|rd)\s+century',
            od, re.IGNORECASE,
        )
        if m:
            period = m.group(1).lower()
            century = int(m.group(2))
            base = (century - 1) * 100
            offsets = {'early': 20, 'mid': 50, 'late': 80}
            return base + offsets.get(period, 50)

    # 4. Era lookup
    if product.era:
        era_lower = product.era.lower().strip()
        for era_key, year in ERA_YEAR_MAP.items():
            if era_key in era_lower:
                return year

    return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_structural_score(source, target):
    """
    Compute structural similarity using Fashionpedia taxonomy fields.
    Returns (score, shared_attributes_dict).
    """
    score = 0.0
    shared = {}

    for field, weight in STRUCTURAL_WEIGHTS.items():
        s_val = getattr(source, field, None)
        t_val = getattr(target, field, None)

        if not s_val or not t_val:
            continue

        if field in SET_FIELDS:
            try:
                s_set = set(json.loads(s_val)) if isinstance(s_val, str) else set(s_val)
                t_set = set(json.loads(t_val)) if isinstance(t_val, str) else set(t_val)
            except (json.JSONDecodeError, TypeError):
                continue

            if not s_set or not t_set:
                continue

            intersection = s_set & t_set
            union = s_set | t_set
            jaccard = len(intersection) / len(union)
            score += weight * jaccard
            if intersection:
                shared[field] = sorted(intersection)
        else:
            if s_val.strip().lower() == t_val.strip().lower():
                score += weight
                shared[field] = s_val.strip()

    return round(score, 4), shared


def classify_temporal_type(source_platform, target_platform,
                           source_year, target_year) -> str:
    """Classify bridge type by temporal distance. Date-first, platform fallback."""

    if source_year is not None and target_year is not None:
        distance = abs(source_year - target_year)
        if distance > CROSS_ERA_DISTANCE:
            return 'cross_era'
        elif distance > NEAR_ERA_DISTANCE:
            return 'near_era'
        else:
            return 'same_era'

    # Fallback: use platform as temporal proxy
    s_hist = source_platform in HISTORICAL_PLATFORMS
    t_hist = target_platform in HISTORICAL_PLATFORMS

    if s_hist != t_hist:
        return 'cross_era'
    else:
        return 'same_era'


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

def get_all_ids(vdb, collection_name: str) -> set:
    """Get all point IDs in a Qdrant collection."""
    ids = set()
    offset = None
    while True:
        points, offset = vdb.client.scroll(
            collection_name=collection_name,
            limit=256,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        for p in points:
            ids.add(p.id)
        if offset is None:
            break
    return ids


# ---------------------------------------------------------------------------
# Filter builders
# ---------------------------------------------------------------------------

def build_open_filter(product):
    """No restrictions, just exclude self."""
    return Filter(must_not=[HasIdCondition(has_id=[product.id])])


def build_cross_category_filter(product):
    """Exclude same garment category + self. Returns None if no category."""
    if not product.fp_category:
        return None
    return Filter(must_not=[
        HasIdCondition(has_id=[product.id]),
        FieldCondition(
            key="fp_category",
            match=MatchValue(value=product.fp_category),
        ),
    ])


def build_cross_vibe_filter(product):
    """Exclude same vibe + self. Returns None if no vibe."""
    if not product.vibe:
        return None
    return Filter(must_not=[
        HasIdCondition(has_id=[product.id]),
        FieldCondition(
            key="vibe",
            match=MatchValue(value=product.vibe),
        ),
    ])


# ---------------------------------------------------------------------------
# Search + score helpers
# ---------------------------------------------------------------------------

def search_candidates(vdb, text_vector, image_vector, qfilter, image_ids,
                      top_k):
    """Search text + image collections with a filter, merge candidates."""
    candidates = {}

    text_results = vdb.client.search(
        collection_name=vdb.text_collection,
        query_vector=text_vector,
        query_filter=qfilter,
        limit=top_k,
    )
    for hit in text_results:
        candidates[hit.id] = {'text_score': hit.score, 'image_score': None}

    if image_vector is not None:
        image_results = vdb.client.search(
            collection_name=vdb.image_collection,
            query_vector=image_vector,
            query_filter=qfilter,
            limit=top_k,
        )
        for hit in image_results:
            if hit.id in candidates:
                candidates[hit.id]['image_score'] = hit.score
            else:
                candidates[hit.id] = {
                    'text_score': None,
                    'image_score': hit.score,
                }

    return candidates


def score_candidates(product, candidates, product_map, year_map,
                     min_structural, min_bridge, bridge_type_override=None):
    """
    Score candidates against a product. Returns (bridges_list, stats_dict).
    If bridge_type_override is set, all bridges get that type.
    Otherwise uses temporal classification.
    """
    bridges = []
    source_year = year_map.get(product.id)
    stats = {'skipped_structural': 0, 'skipped_bridge': 0}

    for cand_id, scores in candidates.items():
        if cand_id == product.id:
            continue
        target = product_map.get(cand_id)
        if target is None:
            continue

        # Skip near-duplicates: same title on same platform
        if (product.platform == target.platform
                and product.title and target.title
                and product.title.strip().lower() == target.title.strip().lower()):
            stats['skipped_structural'] += 1
            continue

        structural_score, shared = compute_structural_score(product, target)
        if structural_score < min_structural:
            stats['skipped_structural'] += 1
            continue

        text_sim = scores['text_score'] or 0.0
        image_sim = scores['image_score']

        # Composite bridge score (redistribute weight when no image)
        if image_sim is not None:
            bridge_score = (0.40 * text_sim
                            + 0.30 * image_sim
                            + 0.30 * structural_score)
        else:
            bridge_score = 0.55 * text_sim + 0.45 * structural_score

        bridge_score = round(bridge_score, 4)

        if bridge_score < min_bridge:
            stats['skipped_bridge'] += 1
            continue

        if bridge_type_override:
            bridge_type = bridge_type_override
        else:
            target_year = year_map.get(cand_id)
            bridge_type = classify_temporal_type(
                product.platform, target.platform,
                source_year, target_year,
            )

        # Canonical ordering: always store min(id) -> max(id) so the
        # unique constraint catches the reverse direction automatically.
        lo, hi = min(product.id, cand_id), max(product.id, cand_id)

        bridges.append({
            'source_id': lo,
            'target_id': hi,
            'text_similarity': round(text_sim, 4),
            'image_similarity': round(image_sim, 4) if image_sim is not None else None,
            'structural_score': round(structural_score, 4),
            'bridge_score': bridge_score,
            'shared_attributes': json.dumps(shared),
            'bridge_type': bridge_type,
            'created_at': datetime.utcnow(),
        })

    return bridges, stats


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def compute_bridges(rebuild=False, limit=None,
                    top_k=20, top_n=10,
                    min_structural=0.15, min_bridge=0.30):
    """
    Compute style bridges with three passes per product:
      1. Open discovery  (top_n bridges, temporal classification)
      2. Cross-category  (top_n//2 bridges, different fp_category)
      3. Cross-vibe      (top_n//2 bridges, different vibe)
    """
    db = SessionLocal()
    vdb = VectorDB()

    print("\n" + "=" * 70)
    print("COMPUTING STYLE BRIDGES")
    print("  3 passes: open | cross-category | cross-vibe")
    print("  Date-first temporal classification")
    print("=" * 70)

    # --- Load products -------------------------------------------------
    products = db.query(Product).filter(Product.enriched_at != None).all()
    product_map = {p.id: p for p in products}

    # Pre-compute approximate years
    year_map = {}
    dated_count = 0
    for p in products:
        y = extract_approximate_year(p)
        year_map[p.id] = y
        if y is not None:
            dated_count += 1

    # --- Check Qdrant --------------------------------------------------
    text_ids = get_all_ids(vdb, vdb.text_collection)
    image_ids = get_all_ids(vdb, vdb.image_collection)

    eligible = [p for p in products if p.id in text_ids]
    if limit:
        eligible = eligible[:limit]

    by_platform = {}
    for p in eligible:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print(f"\n  Enriched products:       {len(products)}")
    print(f"  With approximate year:   {dated_count}/{len(products)}")
    print(f"  Text-embedded (Qdrant):  {len(text_ids)}")
    print(f"  Image-embedded (Qdrant): {len(image_ids)}")
    print(f"  Eligible for bridging:   {len(eligible)}")
    print(f"\n  By platform:")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {platform:20s} {count:4d}")

    if not eligible:
        print("\n  No eligible products. Embed products into Qdrant first.")
        db.close()
        return

    if rebuild:
        deleted = db.query(StyleBridge).delete()
        db.commit()
        print(f"\n  Cleared {deleted} existing bridges.")

    # Define passes: (name, top_n, filter_builder, bridge_type_override)
    passes = [
        ('open',           top_n,      build_open_filter,           None),
        ('cross_category', top_n // 2, build_cross_category_filter, 'cross_category'),
        ('cross_vibe',     top_n // 2, build_cross_vibe_filter,     'cross_vibe'),
    ]

    print(f"\n  Parameters: top_k={top_k}  min_structural={min_structural}  "
          f"min_bridge={min_bridge}")
    print(f"  Per product: open={top_n}  cross_category={top_n // 2}  "
          f"cross_vibe={top_n // 2}")
    print("\n" + "-" * 70)
    print("Starting...\n")

    total_stored = 0
    total_by_pass = {name: 0 for name, *_ in passes}
    skipped_structural = 0
    skipped_bridge = 0
    start_time = time.time()

    for i, product in enumerate(eligible):
        # --- Retrieve source vectors (once per product) ----------------
        text_pts = vdb.client.retrieve(
            collection_name=vdb.text_collection,
            ids=[product.id],
            with_vectors=True,
        )
        if not text_pts:
            continue
        text_vector = text_pts[0].vector

        image_vector = None
        if product.id in image_ids:
            img_pts = vdb.client.retrieve(
                collection_name=vdb.image_collection,
                ids=[product.id],
                with_vectors=True,
            )
            if img_pts:
                image_vector = img_pts[0].vector

        product_bridges = 0

        # --- Run each pass ---------------------------------------------
        for pass_name, pass_top_n, filter_fn, type_override in passes:
            qfilter = filter_fn(product)
            if qfilter is None:
                continue

            candidates = search_candidates(
                vdb, text_vector, image_vector, qfilter, image_ids, top_k,
            )

            bridges, stats = score_candidates(
                product, candidates, product_map, year_map,
                min_structural, min_bridge, type_override,
            )

            skipped_structural += stats['skipped_structural']
            skipped_bridge += stats['skipped_bridge']

            # Keep top N for this pass
            bridges.sort(key=lambda b: b['bridge_score'], reverse=True)
            bridges = bridges[:pass_top_n]

            # Insert (ON CONFLICT DO NOTHING for idempotent re-runs)
            for b in bridges:
                if b['source_id'] == b['target_id']:
                    continue  # never bridge an item to itself
                stmt = pg_insert(StyleBridge.__table__).values(**b)
                stmt = stmt.on_conflict_do_nothing(constraint='uq_bridge_pair')
                db.execute(stmt)

            product_bridges += len(bridges)
            total_by_pass[pass_name] += len(bridges)

        total_stored += product_bridges
        if product_bridges:
            db.commit()

        # Progress
        if (i + 1) % 25 == 0 or (i + 1) == len(eligible):
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(eligible) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:4d}/{len(eligible)}]  "
                  f"{total_stored:5d} bridges  "
                  f"{rate:.1f} items/s  "
                  f"ETA {eta:.0f}s")

    db.commit()
    elapsed = time.time() - start_time

    # --- Summary -------------------------------------------------------
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"\n  Products processed:       {len(eligible)}")
    print(f"  Bridges stored:           {total_stored}")
    print(f"  Skipped (low structural): {skipped_structural}")
    print(f"  Skipped (low bridge):     {skipped_bridge}")
    print(f"  Time:                     {elapsed:.1f}s")

    print(f"\n  By pass:")
    for name, count in total_by_pass.items():
        print(f"    {name:25s} {count:5d}")

    # Bridge type breakdown from DB
    type_counts = (
        db.query(StyleBridge.bridge_type, func.count())
        .group_by(StyleBridge.bridge_type)
        .all()
    )
    if type_counts:
        print(f"\n  By bridge type (all in DB):")
        for bt, count in sorted(type_counts, key=lambda x: -x[1]):
            print(f"    {bt or 'null':25s} {count:5d}")

    # Top bridges
    top = (
        db.query(StyleBridge)
        .order_by(StyleBridge.bridge_score.desc())
        .limit(5)
        .all()
    )
    if top:
        print(f"\n  Top 5 bridges:")
        for b in top:
            src = product_map.get(b.source_id)
            tgt = product_map.get(b.target_id)
            s_name = src.title[:30] if src else f"#{b.source_id}"
            t_name = tgt.title[:30] if tgt else f"#{b.target_id}"
            s_yr = year_map.get(b.source_id, '?')
            t_yr = year_map.get(b.target_id, '?')
            print(f"    {b.bridge_score:.3f}  [{b.bridge_type}]")
            print(f"      {s_name} ({s_yr})")
            print(f"      -> {t_name} ({t_yr})")
            if b.shared_attributes:
                attrs = json.loads(b.shared_attributes)
                preview = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
                print(f"      shared: {preview}")

    db.close()


if __name__ == '__main__':
    rebuild_flag = '--rebuild' in sys.argv
    limit_val = None
    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=')[1])
        elif not arg.startswith('--'):
            try:
                limit_val = int(arg)
            except ValueError:
                pass

    compute_bridges(rebuild=rebuild_flag, limit=limit_val)
