"""
Re-classify existing bridges using the inline classification logic.

Useful for re-running classification after logic changes without recomputing bridges.
All classification logic lives in compute_bridges.py — this script just applies it.

Usage:
  python tools/analysis/classify_bridge_dimensions.py                # full run
  python tools/analysis/classify_bridge_dimensions.py --dry-run      # report only
  python tools/analysis/classify_bridge_dimensions.py --limit=50     # test subset
"""
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product, StyleBridge
from tools.analysis.compute_bridges import classify_bridge, _parse_vibe_axes
from sqlalchemy import func


def run(limit=None, dry_run=False):
    """Re-classify all bridges using inline classification logic."""
    db = SessionLocal()

    products = db.query(Product).all()
    product_map = {p.id: p for p in products}
    print(f"Loaded {len(product_map)} products")

    query = db.query(StyleBridge)
    if limit:
        query = query.limit(limit)
    bridges = query.all()
    print(f"Re-classifying {len(bridges)} bridges{'  (dry run)' if dry_run else ''}\n")

    classified = 0
    missing_vibes = 0
    missing_products = 0

    for bridge in bridges:
        src = product_map.get(bridge.source_id)
        tgt = product_map.get(bridge.target_id)
        if not src or not tgt:
            missing_products += 1
            continue

        # Build a dict from bridge ORM, classify, write back
        bridge_dict = {
            'source_id': bridge.source_id,
            'target_id': bridge.target_id,
            'text_similarity': bridge.text_similarity,
            'image_similarity': bridge.image_similarity,
            'structural_score': bridge.structural_score,
            'shared_attributes': bridge.shared_attributes,
            'bridge_type': bridge.bridge_type,
        }

        src_axes = _parse_vibe_axes(src)
        tgt_axes = _parse_vibe_axes(tgt)
        if not src_axes or not tgt_axes:
            missing_vibes += 1

        classify_bridge(src, tgt, bridge_dict)

        bridge.temporal_type = bridge_dict['temporal_type']
        bridge.crossing_type = bridge_dict['crossing_type']
        bridge.connection_mode = bridge_dict['connection_mode']
        bridge.primary_axis = bridge_dict['primary_axis']
        bridge.secondary_axis = bridge_dict['secondary_axis']
        bridge.contrast_pair = bridge_dict['contrast_pair']

        classified += 1

    if not dry_run:
        db.commit()
        print(f"Committed {classified} bridges\n")
    else:
        print(f"Would classify {classified} bridges\n")

    if missing_products:
        print(f"  Skipped (missing product): {missing_products}")
    if missing_vibes:
        print(f"  Missing vibe_axes on one/both products: {missing_vibes}")

    # Distribution stats
    print("\n--- temporal_type ---")
    for row in db.query(StyleBridge.temporal_type, func.count()).group_by(
            StyleBridge.temporal_type).all():
        print(f"  {row[0] or 'NULL':20s} {row[1]:>6}")

    print("\n--- crossing_type ---")
    for row in db.query(StyleBridge.crossing_type, func.count()).group_by(
            StyleBridge.crossing_type).all():
        print(f"  {row[0] or 'NULL':30s} {row[1]:>6}")

    print("\n--- connection_mode ---")
    for row in db.query(StyleBridge.connection_mode, func.count()).group_by(
            StyleBridge.connection_mode).all():
        print(f"  {row[0] or 'NULL':20s} {row[1]:>6}")

    print("\n--- primary_axis ---")
    for row in db.query(StyleBridge.primary_axis, func.count()).group_by(
            StyleBridge.primary_axis).all():
        print(f"  {row[0] or 'NULL':20s} {row[1]:>6}")

    print("\n--- contrast pairs ---")
    contrasts = db.query(StyleBridge.contrast_pair, func.count()).filter(
        StyleBridge.contrast_pair != None
    ).group_by(StyleBridge.contrast_pair).all()
    if contrasts:
        for row in sorted(contrasts, key=lambda x: -x[1]):
            print(f"  {row[0]:50s} {row[1]:>6}")
    else:
        print("  (none)")

    db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Re-classify bridges (thin wrapper around compute_bridges.classify_bridge)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
