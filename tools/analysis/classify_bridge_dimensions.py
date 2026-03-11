"""
Multi-dimensional bridge classification.

Replaces the single semantic_type column with 6 orthogonal dimensions:
    temporal_type, crossing_type, connection_mode, primary_axis, secondary_axis, contrast_pair

Usage:
  python scripts/classify_bridge_dimensions.py                # full run
  python scripts/classify_bridge_dimensions.py --dry-run      # report only
  python scripts/classify_bridge_dimensions.py --limit=50     # test subset
"""
import sys, os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product, StyleBridge
from tools.analysis.compute_bridges import (
    CATEGORY_GROUPS, _CAT_TO_GROUP, _get_category_group,
    classify_temporal_type,
)
from sqlalchemy import func


# ---------------------------------------------------------------------------
# Opposition pairs for contrast detection (9 pairs)
# ---------------------------------------------------------------------------

OPPOSITION_PAIRS = [
    ("Exaggerated Volume",            "Column Minimalism",            "volume"),
    ("Constructed Armor",             "Draped Fluidity",              "volume"),
    ("Constructed Armor",             "Body Liberation",              "volume"),
    ("Maximalist Ornament",           "Austere Restraint",            "ornament"),
    ("Transparency and Revelation",   "Body Concealment",             "ornament"),
    ("Body Liberation",               "Body Transformation",          "body"),
    ("Body Display",                  "Body Concealment",             "body"),
    ("Transgressive Subversion",      "Elite Distinction",            "register"),
    ("Pastoral Naturalism",           "Ceremonial Formalism",         "register"),
]


# ---------------------------------------------------------------------------
# Structural field -> axis mapping
# ---------------------------------------------------------------------------

FIELD_TO_AXIS = {
    'silhouette':               ['volume'],
    'fit_style':                ['volume'],
    'material':                 ['ornament'],
    'colors':                   ['ornament'],
    'textile_pattern':          ['ornament'],
    'textile_finishing':        ['ornament'],
    'decorations':              ['ornament'],
    'garment_type':             ['body'],
    'neckline':                 ['body'],
    'sleeve_length':            ['body'],
    'waistline':                ['body'],
    'length':                   ['body'],
    'occasion':                 ['register'],
    'social_function':          ['register'],
    'culture':                  ['register'],
    'construction_technique':   ['volume', 'ornament'],  # splits 0.5 each
}


# ---------------------------------------------------------------------------
# Vibe term -> axis (for reference / future use)
# ---------------------------------------------------------------------------

VIBE_TO_AXIS = {
    'Exaggerated Volume': 'volume', 'Column Minimalism': 'volume',
    'Empire Suspension': 'volume', 'Constructed Armor': 'volume',
    'Draped Fluidity': 'volume', 'Layered Accumulation': 'volume',
    'Maximalist Ornament': 'ornament', 'Austere Restraint': 'ornament',
    'Handcraft Visibility': 'ornament', 'Material Luxury': 'ornament',
    'Pattern as Language': 'ornament', 'Transparency and Revelation': 'ornament',
    'Body Liberation': 'body', 'Body Transformation': 'body',
    'Body Concealment': 'body', 'Body Display': 'body',
    'Pastoral Naturalism': 'register', 'Ceremonial Formalism': 'register',
    'Dark Romanticism': 'register', 'Transgressive Subversion': 'register',
    'Nostalgic Revival': 'register', 'Elite Distinction': 'register',
}

# Historical platforms (used as temporal proxy when era is missing)
HISTORICAL_PLATFORMS = {'met_museum', 'smithsonian', 'va_museum'}


# ===========================================================================
# CLASSIFICATION FUNCTIONS
# ===========================================================================


def classify_crossing_type(source, target):
    """Derive categorical/cultural crossing from product data.
    Returns: 'same_context' | 'cross_category' | 'cross_culture' | 'cross_category_culture'
    """
    diff_category = False
    diff_culture = False

    src_group = _get_category_group(source.fp_category)
    tgt_group = _get_category_group(target.fp_category)
    if src_group and tgt_group and src_group != tgt_group:
        diff_category = True

    src_culture = (source.culture or '').strip().lower()
    tgt_culture = (target.culture or '').strip().lower()
    if src_culture and tgt_culture and src_culture != tgt_culture:
        diff_culture = True

    if diff_category and diff_culture:
        return 'cross_category_culture'
    if diff_category:
        return 'cross_category'
    if diff_culture:
        return 'cross_culture'
    return 'same_context'


def classify_connection_mode(bridge, source, target):
    """Derive aesthetic connection mode + axes + contrast pair.

    Must be called AFTER bridge.temporal_type is set.
    Returns: (connection_mode, primary_axis, secondary_axis, contrast_pair)
    """
    text_sim = bridge.text_similarity or 0
    structural = bridge.structural_score or 0
    shared = json.loads(bridge.shared_attributes or '{}')

    src_vibes = set(source.core_vibes or []) | set(source.bridge_vibes or [])
    tgt_vibes = set(target.core_vibes or []) | set(target.bridge_vibes or [])

    # 1. CONTRAST: opposition on a vibe axis, grounded in shared structure
    contrast_result = _detect_contrast(src_vibes, tgt_vibes, structural)
    if contrast_result:
        pair_str, axis = contrast_result
        return ('contrast', axis, None, pair_str)

    # 2. RESONANCE: same aesthetic language across time
    if text_sim >= 0.85 and bridge.temporal_type == 'transmission':
        axes = _derive_axes_from_shared(shared)
        return ('resonance', axes[0], axes[1], None)

    # 3. AFFINITY: family resemblance — axis tells the story
    axes = _derive_axes_from_shared(shared)
    return ('affinity', axes[0], axes[1], None)


# ===========================================================================
# HELPERS
# ===========================================================================

def _detect_contrast(src_vibes, tgt_vibes, structural_score):
    """Check if source and target hold opposing vibes on any axis.
    Returns: (pair_string, axis) or None
    """
    if structural_score < 0.4:
        return None

    for vibe_a, vibe_b, axis in OPPOSITION_PAIRS:
        if ((vibe_a in src_vibes and vibe_b in tgt_vibes) or
                (vibe_b in src_vibes and vibe_a in tgt_vibes)):
            return (f"{vibe_a} <-> {vibe_b}", axis)
    return None


def _derive_axes_from_shared(shared_attrs):
    """Count shared attributes by axis, return (primary, secondary).
    Returns: (primary_axis_or_None, secondary_axis_or_None)
    """
    axis_counts = {'volume': 0, 'ornament': 0, 'body': 0, 'register': 0}

    for field in shared_attrs:
        axes = FIELD_TO_AXIS.get(field, [])
        if len(axes) == 1:
            axis_counts[axes[0]] += 1
        elif len(axes) == 2:
            for a in axes:
                axis_counts[a] += 0.5

    ranked = sorted(
        [(axis, count) for axis, count in axis_counts.items() if count > 0],
        key=lambda x: -x[1]
    )

    primary = ranked[0][0] if len(ranked) >= 1 else None
    secondary = ranked[1][0] if len(ranked) >= 2 else None
    return (primary, secondary)


# ===========================================================================
# MAIN
# ===========================================================================

def run(limit=None, dry_run=False):
    """Classify all bridges across 6 dimensions."""
    db = SessionLocal()

    products = db.query(Product).all()
    product_map = {p.id: p for p in products}
    print(f"Loaded {len(product_map)} products")

    query = db.query(StyleBridge)
    if limit:
        query = query.limit(limit)
    bridges = query.all()
    print(f"Classifying {len(bridges)} bridges{'  (dry run)' if dry_run else ''}\n")

    classified = 0
    missing_vibes = 0
    missing_products = 0

    for bridge in bridges:
        src = product_map.get(bridge.source_id)
        tgt = product_map.get(bridge.target_id)
        if not src or not tgt:
            missing_products += 1
            continue

        # Step 1: temporal_type
        bridge.temporal_type = classify_temporal_type(
            src.era, tgt.era,
            src.platform, tgt.platform,
            src.decade, tgt.decade,
        )


        # Step 2: crossing_type
        bridge.crossing_type = classify_crossing_type(src, tgt)

        # Step 3: connection_mode + axes + contrast_pair
        if not (src.core_vibes and tgt.core_vibes):
            missing_vibes += 1

        mode, primary, secondary, contrast = classify_connection_mode(bridge, src, tgt)
        bridge.connection_mode = mode
        bridge.primary_axis = primary
        bridge.secondary_axis = secondary
        bridge.contrast_pair = contrast

        classified += 1

    if not dry_run:
        db.commit()
        print(f"Committed {classified} bridges\n")
    else:
        print(f"Would classify {classified} bridges\n")

    if missing_products:
        print(f"  Skipped (missing product): {missing_products}")
    if missing_vibes:
        print(f"  Missing core_vibes on one/both products: {missing_vibes}")

    # --- Distribution stats ---
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
    parser = argparse.ArgumentParser(description='Classify bridges across 6 dimensions')
    parser.add_argument('--dry-run', action='store_true', help='Report only, do not commit')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of bridges')
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
