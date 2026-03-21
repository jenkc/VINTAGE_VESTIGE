"""
Compute style bridges between enriched products.
"""

import sys
import os
import json
import time
import numpy as np
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product, StyleBridge, engine
from enrichment.era_taxonomy import ERAS
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func, text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTINUATION_DISTANCE = 20   # min decade gap within same era
TRANSMISSION_DISTANCE = 40   # min era midpoint gap for transmission
BOUNDARY_YEAR_GAP = 20       # min year gap for cross-context boundary

# Pre-compute era midpoints
_ERA_MIDPOINTS = {}
for _name, _data in ERAS.items():
    _ERA_MIDPOINTS[_name.strip().lower()] = (_data['start'] + _data['end']) // 2

# Structural field weights (sum to 1.0)
STRUCTURAL_WEIGHTS = {
    # Fashionpedia structural (0.42 total)
    'fp_category':              0.05,
    'silhouette':               0.08,
    'nickname':                 0.05,
    'neckline':                 0.05,
    'length':                   0.05,
    'waistline':                0.04,
    'sleeve_length':            0.04,
    'textile_pattern':          0.04,
    'opening_type':             0.02,
    # Fashionpedia arrays (0.08 total)
    'garment_parts':            0.03,   # Jaccard
    'decorations':              0.02,   # Jaccard
    'textile_finishing':        0.03,   # Jaccard
    # Cross-cultural (0.30 total)
    'construction_technique':   0.12,   # Jaccard
    'social_function':          0.10,   # Jaccard
    'motif_family':             0.08,   # Jaccard
    # Knowledge graph (0.20 total)
    'influence_references':     0.06,   # Jaccard — shared historical references
    'named_movements':          0.06,   # Jaccard — shared design movements
    'garment_system':           0.04,   # Jaccard — shared body philosophy
    'designer':                 0.04,   # Exact match — same maker
}

SET_FIELDS = {'garment_parts', 'decorations', 'textile_finishing',
              'construction_technique', 'social_function', 'motif_family',
              'influence_references', 'named_movements', 'garment_system'}
CROSS_CULTURAL_FIELDS = {'construction_technique', 'social_function', 'motif_family',
                         'influence_references', 'named_movements'}

# 6-axis vibe system — each axis has two opposing poles
AXIS_POLES = {
    "volume":   ("Exaggerated Volume",        "Column Minimalism"),
    "ornament": ("Maximalist Ornament",       "Bare Surface"),
    "exposure": ("Body Display",              "Body Concealment"),
    "gender":   ("Gender Conforming",         "Gender Defiant"),
    "register": ("Transgressive Subversion",  "Elite Distinction"),
    "occasion": ("Pastoral Naturalism",       "Ceremonial Formalism"),
}

OPPOSITION_PAIRS = [(a, b, axis) for axis, (a, b) in AXIS_POLES.items()]

# Category groups for boundary detection
CATEGORY_GROUPS = {
    'tops':      {'blouse', 'shirt', 'top', 't-shirt', 'sweater', 'tank top', 'camisole', 'bodysuit'},
    'outerwear': {'coat', 'jacket', 'blazer', 'cape', 'vest', 'cardigan', 'poncho', 'parka'},
    'bottoms':   {'pants', 'shorts', 'trousers', 'jeans', 'leggings', 'culottes'},
    'dresses':   {'dress', 'gown', 'robe', 'jumpsuit', 'romper'},
    'skirts':    {'skirt', 'mini skirt', 'maxi skirt'},
}

_CAT_TO_GROUP = {}
for group, cats in CATEGORY_GROUPS.items():
    for cat in cats:
        _CAT_TO_GROUP[cat] = group

# Structural field -> classification axis mapping
FIELD_TO_AXIS = {
    'silhouette': ['volume'], 'fit_style': ['volume'],
    'material': ['ornament'], 'colors': ['ornament'],
    'textile_pattern': ['ornament'], 'textile_finishing': ['ornament'],
    'decorations': ['ornament'],
    'garment_type': ['exposure'], 'neckline': ['exposure'],
    'sleeve_length': ['exposure'], 'waistline': ['exposure'], 'length': ['exposure'],
    'occasion': ['occasion'], 'social_function': ['occasion'],
    'culture': ['register'],
    'construction_technique': ['volume', 'ornament'],
}


# ===========================================================================
# Scoring
# ===========================================================================

def compute_structural_score(source, target):
    """Compute structural similarity. Returns (score, shared_attributes_dict)."""
    score = 0.0
    shared = {}
    for field, weight in STRUCTURAL_WEIGHTS.items():
        s_val = getattr(source, field, None)
        t_val = getattr(target, field, None)
        if not s_val or not t_val:
            continue
        if field in SET_FIELDS:
            s_set = getattr(source, f'_{field}_set', set())
            t_set = getattr(target, f'_{field}_set', set())
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


def parse_decade_to_year(decade: str | None) -> int | None:
    if not decade:
        return None
    d = decade.strip().rstrip('s')
    try:
        return int(d) + 5
    except ValueError:
        return None


# ===========================================================================
# Temporal classification
# ===========================================================================

def classify_temporal_type(source_era, target_era,
                           source_decade=None, target_decade=None) -> str | None:
    """Classify temporal relationship using era and decade data only.

    Returns: echo (80+ yr) | transmission (40-79 yr) | continuation (same era, 20+ yr)
             | contemporary (same era, close) | None (insufficient data)
    """
    # Try decade midpoints first — most precise
    src_yr = parse_decade_to_year(source_decade)
    tgt_yr = parse_decade_to_year(target_decade)
    if src_yr and tgt_yr:
        gap = abs(src_yr - tgt_yr)
        if gap >= 80:
            return 'echo'
        if gap >= TRANSMISSION_DISTANCE:
            return 'transmission'
        if gap >= CONTINUATION_DISTANCE:
            return 'continuation'
        return 'contemporary'

    # Fall back to era midpoints
    if source_era and target_era:
        src_key = source_era.strip().lower()
        tgt_key = target_era.strip().lower()
        if src_key == tgt_key:
            return 'contemporary'
        src_mid = _ERA_MIDPOINTS.get(src_key)
        tgt_mid = _ERA_MIDPOINTS.get(tgt_key)
        if src_mid is not None and tgt_mid is not None:
            gap = abs(src_mid - tgt_mid)
            if gap >= 80:
                return 'echo'
            if gap >= TRANSMISSION_DISTANCE:
                return 'transmission'
            return 'contemporary'
        # Different named eras but no midpoints — assume transmission
        return 'transmission'

    return None


# ===========================================================================
# Vibe axis helpers
# ===========================================================================

def _parse_vibe_axes(product) -> dict:
    """Extract vibe axes from product.vibe_scores JSON.
    Returns: {axis_name: (pole_name, confidence)}
    """
    raw = getattr(product, 'vibe_scores', None)
    if not raw:
        return {}
    try:
        axes = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(axes, dict):
            return {}
        result = {}
        for axis, val in axes.items():
            if isinstance(val, list) and len(val) >= 2:
                result[axis] = (val[0], val[1])
        return result
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_vibes(product) -> set:
    """Extract pole names as a set."""
    axes = _parse_vibe_axes(product)
    return {pole for pole, _conf in axes.values()}


# ===========================================================================
# Boundary crossing & classification helpers
# ===========================================================================

def _get_category_group(fp_category):
    if not fp_category:
        return None
    return _CAT_TO_GROUP.get(fp_category.strip().lower(), fp_category.strip().lower())


def _get_year_gap(source, target) -> float | None:
    """Get year gap between two products using decades or era midpoints."""
    src_yr = parse_decade_to_year(source.decade)
    tgt_yr = parse_decade_to_year(target.decade)
    if src_yr and tgt_yr:
        return abs(src_yr - tgt_yr)
    src_mid = _ERA_MIDPOINTS.get((source.era or '').strip().lower())
    tgt_mid = _ERA_MIDPOINTS.get((target.era or '').strip().lower())
    if src_mid is not None and tgt_mid is not None:
        return abs(src_mid - tgt_mid)
    return None


def compute_bridge_score(text_sim, image_sim, structural_score):
    """Precompute composite bridge score. Structural-heavy weighting."""
    if image_sim is not None:
        return round(0.30 * text_sim + 0.25 * image_sim + 0.45 * structural_score, 4)
    else:
        # Redistribute image weight proportionally
        return round(0.40 * text_sim + 0.60 * structural_score, 4)


def _extract_kg_bridge_fields(source, target):
    """Extract shared KG fields between two products for bridge-level storage."""
    result = {}

    # Shared designer
    s_designer = getattr(source, 'designer', None)
    t_designer = getattr(target, 'designer', None)
    if s_designer and t_designer and s_designer.strip().lower() == t_designer.strip().lower():
        result['shared_designer'] = s_designer.strip()

    # Shared movements (Jaccard-style intersection)
    s_mov = getattr(source, '_named_movements_set', set())
    t_mov = getattr(target, '_named_movements_set', set())
    shared_mov = s_mov & t_mov
    if shared_mov:
        result['shared_movements'] = json.dumps(sorted(shared_mov))

    # Shared influences
    s_infl = getattr(source, '_influence_references_set', set())
    t_infl = getattr(target, '_influence_references_set', set())
    shared_infl = s_infl & t_infl
    if shared_infl:
        result['shared_influences'] = json.dumps(sorted(shared_infl))

    return result


def _detect_lineage(source, target):
    """True if one product's influence_references cites something the other product IS.

    Checks if any influence reference from A matches B's era, named_movements,
    garment_type, or nickname — or vice versa.
    """
    def _references_match(influences_set, other):
        if not influences_set:
            return False
        # Build a set of terms that describe what the other product IS
        identity = set()
        if other.era:
            identity.add(other.era.strip().lower())
        if getattr(other, 'garment_type', None):
            identity.add(other.garment_type.strip().lower())
        if getattr(other, 'nickname', None):
            identity.add(other.nickname.strip().lower())
        # Named movements
        other_mov = getattr(other, '_named_movements_set', set())
        identity.update(m.lower() for m in other_mov)

        # Check if any influence reference contains a term from the other's identity
        for ref in influences_set:
            ref_lower = ref.lower()
            for term in identity:
                if term in ref_lower or ref_lower in term:
                    return True
        return False

    s_infl = getattr(source, '_influence_references_set', set())
    t_infl = getattr(target, '_influence_references_set', set())

    return _references_match(s_infl, target) or _references_match(t_infl, source)


def _too_similar(text_sim, image_sim, same_era=False):
    """True if a pair is too similar to be an interesting bridge.
    A high score on one dimension is fine (visually similar but different description = interesting).
    Both dimensions being high means it's basically the same item.
    Same-era pairs with high text similarity are near-duplicates.
    """
    # Same era + high text similarity = near-duplicate
    if same_era and text_sim >= 0.85:
        return True
    # Both dimensions high = basically the same item
    if image_sim is not None and image_sim >= 0.95 and text_sim >= 0.70:
        return True
    if image_sim is not None and image_sim >= 0.85 and text_sim >= 0.80:
        return True
    # Combined average too high = near-duplicate regardless of era
    if image_sim is not None and (text_sim + image_sim) / 2 >= 0.85:
        return True
    return False


def _crosses_boundary(source, target, min_year_gap=BOUNDARY_YEAR_GAP):
    """True if products cross era (20+ yr gap) or culture.
    Returns False if neither can be established (drops the pair).
    """
    # Culture crossing
    src_culture = (source.culture or '').strip().lower()
    tgt_culture = (target.culture or '').strip().lower()
    if src_culture and tgt_culture and src_culture != tgt_culture:
        return True
    # Era/decade crossing
    gap = _get_year_gap(source, target)
    if gap is not None and gap >= min_year_gap:
        return True
    return False


def classify_crossing_type(source, target):
    """Returns: same_context | cross_category | cross_culture | cross_category_culture"""
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


def _detect_contrast(src_axes, tgt_axes, structural_score):
    """Check if products are on opposite poles of any axis.
    Returns: (pair_string, axis) or None
    """
    if structural_score < 0.4:
        return None
    for axis in AXIS_POLES:
        src_val = src_axes.get(axis)
        tgt_val = tgt_axes.get(axis)
        if src_val and tgt_val and src_val[0] != tgt_val[0]:
            pole_a, pole_b = AXIS_POLES[axis]
            return (f"{pole_a} <-> {pole_b}", axis)
    return None


def _derive_axes_from_shared(shared_attrs):
    """Count shared attributes by axis, return (primary, secondary)."""
    axis_counts = {axis: 0 for axis in AXIS_POLES}
    for field in shared_attrs:
        field_axes = FIELD_TO_AXIS.get(field, [])
        if len(field_axes) == 1:
            if field_axes[0] in axis_counts:
                axis_counts[field_axes[0]] += 1
        elif len(field_axes) == 2:
            for a in field_axes:
                if a in axis_counts:
                    axis_counts[a] += 0.5
    ranked = sorted(
        [(axis, count) for axis, count in axis_counts.items() if count > 0],
        key=lambda x: -x[1]
    )
    primary = ranked[0][0] if len(ranked) >= 1 else None
    secondary = ranked[1][0] if len(ranked) >= 2 else None
    return (primary, secondary)


def _split_shared_attributes(shared_dict):
    """Split shared_attributes into garment fields and discovery metadata."""
    METADATA_KEYS = {
        'discovery', 'axis', 'opposition_pair', 'independent_invention',
        'boundaries_crossed', 'shared_function',
    }
    garment = {k: v for k, v in shared_dict.items() if k not in METADATA_KEYS}
    metadata = {k: v for k, v in shared_dict.items() if k in METADATA_KEYS}
    return garment, metadata


def classify_bridge(source, target, bridge_dict):
    """Set all classification dimensions on bridge_dict. Mutates in place."""
    # year_gap (replaces temporal_type)
    bridge_dict['year_gap'] = int(_get_year_gap(source, target)) if _get_year_gap(source, target) is not None else None

    # crossing_type
    bridge_dict['crossing_type'] = classify_crossing_type(source, target)

    # bridge_score
    bridge_dict['bridge_score'] = compute_bridge_score(
        bridge_dict.get('text_similarity', 0),
        bridge_dict.get('image_similarity'),
        bridge_dict.get('structural_score', 0),
    )

    # Split shared_attributes into garment fields and discovery metadata
    raw_shared = json.loads(bridge_dict.get('shared_attributes', '{}'))
    garment_fields, discovery_meta = _split_shared_attributes(raw_shared)
    bridge_dict['shared_garment_fields'] = json.dumps(garment_fields) if garment_fields else None
    bridge_dict['discovery_metadata'] = json.dumps(discovery_meta) if discovery_meta else None
    del bridge_dict['shared_attributes']

    # KG bridge fields
    kg = _extract_kg_bridge_fields(source, target)
    bridge_dict['shared_designer'] = kg.get('shared_designer')
    bridge_dict['shared_movements'] = kg.get('shared_movements')
    bridge_dict['shared_influences'] = kg.get('shared_influences')

    # connection_mode + axes + contrast_pair
    # Priority: lineage > contrast > echo > parallel > null
    text_sim = bridge_dict.get('text_similarity', 0)
    structural = bridge_dict.get('structural_score', 0)
    year_gap = bridge_dict.get('year_gap')
    crossing = bridge_dict.get('crossing_type', 'same_context')

    # 1. Lineage — explicit influence citation connects the pair
    if _detect_lineage(source, target):
        axes = _derive_axes_from_shared(garment_fields)
        bridge_dict['connection_mode'] = 'lineage'
        bridge_dict['primary_axis'] = axes[0]
        bridge_dict['secondary_axis'] = axes[1]
        bridge_dict['contrast_pair'] = None

    # 2. Contrast — opposite vibe poles
    elif bridge_dict.get('bridge_type') == 'opposition':
        bridge_dict['connection_mode'] = 'contrast'
        bridge_dict['primary_axis'] = discovery_meta.get('axis')
        bridge_dict['secondary_axis'] = None
        bridge_dict['contrast_pair'] = discovery_meta.get('opposition_pair')
    else:
        src_axes = _parse_vibe_axes(source)
        tgt_axes = _parse_vibe_axes(target)
        contrast_result = _detect_contrast(src_axes, tgt_axes, structural)

        if contrast_result:
            pair_str, axis = contrast_result
            bridge_dict['connection_mode'] = 'contrast'
            bridge_dict['primary_axis'] = axis
            bridge_dict['secondary_axis'] = None
            bridge_dict['contrast_pair'] = pair_str

        # 3. Echo — same argument, far apart in time
        elif year_gap is not None and year_gap >= 40 and text_sim >= 0.70:
            axes = _derive_axes_from_shared(garment_fields)
            bridge_dict['connection_mode'] = 'echo'
            bridge_dict['primary_axis'] = axes[0]
            bridge_dict['secondary_axis'] = axes[1]
            bridge_dict['contrast_pair'] = None

        # 4. Visual — looks alike across contexts (visual echo pass, low structural)
        elif bridge_dict.get('bridge_type') == 'visual_echo' and crossing != 'same_context':
            axes = _derive_axes_from_shared(garment_fields)
            bridge_dict['connection_mode'] = 'visual'
            bridge_dict['primary_axis'] = axes[0]
            bridge_dict['secondary_axis'] = axes[1]
            bridge_dict['contrast_pair'] = None

        # 5. Parallel — same argument, different context (culture or category)
        elif crossing != 'same_context' and structural >= 0.30:
            axes = _derive_axes_from_shared(garment_fields)
            bridge_dict['connection_mode'] = 'parallel'
            bridge_dict['primary_axis'] = axes[0]
            bridge_dict['secondary_axis'] = axes[1]
            bridge_dict['contrast_pair'] = None

        # 6. Weak connection — no clear story
        else:
            axes = _derive_axes_from_shared(garment_fields)
            bridge_dict['connection_mode'] = None
            bridge_dict['primary_axis'] = axes[0]
            bridge_dict['secondary_axis'] = axes[1]
            bridge_dict['contrast_pair'] = None


# ===========================================================================
# Embedding helpers
# ===========================================================================

def get_embedded_ids(db):
    text_ids = {r[0] for r in db.execute(
        text("SELECT id FROM products WHERE text_embedding IS NOT NULL")
    ).fetchall()}
    image_ids = {r[0] for r in db.execute(
        text("SELECT id FROM products WHERE image_embedding IS NOT NULL")
    ).fetchall()}
    return text_ids, image_ids


def bulk_load_embeddings(db):
    print("  Loading all embeddings into memory...", end=" ", flush=True)
    rows = db.execute(
        text("SELECT id, text_embedding, image_embedding FROM products "
             "WHERE text_embedding IS NOT NULL OR image_embedding IS NOT NULL")
    ).fetchall()
    cache = {r[0]: (r[1], r[2]) for r in rows}
    print(f"{len(cache)} products loaded.")
    return cache


def _get_embeddings(db, product_id, cache):
    if product_id not in cache:
        row = db.execute(
            text("SELECT text_embedding, image_embedding FROM products WHERE id = :id"),
            {"id": product_id}
        ).fetchone()
        cache[product_id] = (row[0], row[1]) if row else (None, None)
    return cache[product_id]


def _cosine_sim(vec_a, vec_b):
    if vec_a is None or vec_b is None:
        return None
    a = np.array(json.loads(vec_a) if isinstance(vec_a, str) else list(vec_a), dtype=np.float32)
    b = np.array(json.loads(vec_b) if isinstance(vec_b, str) else list(vec_b), dtype=np.float32)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# ===========================================================================
# Insertion helpers
# ===========================================================================

def _insert_bridge(db, bridge_dict, existing_pairs):
    pair = (bridge_dict['source_id'], bridge_dict['target_id'])
    if pair in existing_pairs:
        return False
    clean = {k: v for k, v in bridge_dict.items() if not k.startswith('_')}
    stmt = pg_insert(StyleBridge.__table__).values(**clean)
    stmt = stmt.on_conflict_do_nothing(constraint='uq_bridge_pair')
    result = db.execute(stmt)
    if result.rowcount:
        existing_pairs.add(pair)
        return True
    return False


def _batch_insert_bridges(bridges, existing_pairs, batch_size=100):
    to_insert = [b for b in bridges
                 if (b['source_id'], b['target_id']) not in existing_pairs]
    total_inserted = 0
    for i in range(0, len(to_insert), batch_size):
        batch = to_insert[i:i + batch_size]
        db = SessionLocal()
        batch_inserted = 0
        for b in batch:
            if _insert_bridge(db, b, existing_pairs):
                batch_inserted += 1
        db.commit()
        db.close()
        total_inserted += batch_inserted
    return total_inserted


# ===========================================================================
# Index builders
# ===========================================================================

def build_vibe_index(products):
    """Map each pole name to the set of product IDs scored on that pole."""
    index = {}
    for p in products:
        axes = _parse_vibe_axes(p)
        for axis, (pole, _conf) in axes.items():
            index.setdefault(pole, set()).add(p.id)
    return index


def build_structural_groups(products):
    """Group products by (category_group, silhouette). Skip groups < 3."""
    groups = {}
    for p in products:
        cat = _get_category_group(p.fp_category)
        sil = (p.silhouette or '').strip().lower()
        if cat and sil:
            groups.setdefault((cat, sil), set()).add(p.id)
    return {k: v for k, v in groups.items() if len(v) >= 3}


def preparse_set_fields(product_map):
    """Pre-parse JSON array fields into Python sets for fast structural scoring."""
    for p in product_map.values():
        for field in SET_FIELDS:
            raw = getattr(p, field, None)
            if raw and isinstance(raw, str):
                try:
                    setattr(p, f'_{field}_set', set(json.loads(raw)))
                except (json.JSONDecodeError, TypeError):
                    setattr(p, f'_{field}_set', set())
            elif raw:
                setattr(p, f'_{field}_set', set(raw))
            else:
                setattr(p, f'_{field}_set', set())
    print(f"  Pre-parsed {len(SET_FIELDS)} set fields for {len(product_map)} products")


# ===========================================================================
# Pass 1: Similarity (vector proximity, cross-context only)
# ===========================================================================

def search_candidates_pgvector(db, product_id, text_vector, image_vector, top_k):
    """Search for bridge candidates using pgvector."""
    candidates = {}
    params = {"pid": product_id, "top_k": top_k}

    if text_vector is not None:
        params["text_vec"] = text_vector if isinstance(text_vector, str) else str(list(text_vector))
        rows = db.execute(text("""
            SELECT id, 1 - (text_embedding <=> :text_vec) as score
            FROM products
            WHERE text_embedding IS NOT NULL AND id != :pid
            ORDER BY text_embedding <=> :text_vec
            LIMIT :top_k
        """), params).fetchall()
        for row in rows:
            candidates[row[0]] = {'text_score': row[1], 'image_score': None}

    if image_vector is not None:
        params["img_vec"] = image_vector if isinstance(image_vector, str) else str(list(image_vector))
        rows = db.execute(text("""
            SELECT id, 1 - (image_embedding <=> :img_vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL AND id != :pid
            ORDER BY image_embedding <=> :img_vec
            LIMIT :top_k
        """), params).fetchall()
        for row in rows:
            if row[0] in candidates:
                candidates[row[0]]['image_score'] = row[1]
            else:
                candidates[row[0]] = {'text_score': None, 'image_score': row[1]}

    return candidates


def score_and_filter_candidates(product, candidates, product_map,
                                min_structural, min_bridge):
    """Score candidates for Pass 1. Returns list of bridge dicts."""
    bridges = []
    for cand_id, scores in candidates.items():
        target = product_map.get(cand_id)
        if target is None:
            continue

        # Skip near-duplicates (same title)
        if (product.title and target.title
                and product.title.strip().lower() == target.title.strip().lower()):
            continue

        # Must cross boundary (20+ yr gap OR different culture)
        if not _crosses_boundary(product, target):
            continue

        structural_score, shared = compute_structural_score(product, target)
        if structural_score < min_structural:
            continue

        text_sim = scores['text_score'] or 0.0
        image_sim = scores['image_score']

        # Skip pairs that are too similar to be interesting
        same_era = (product.era and target.era
                    and product.era.strip().lower() == target.era.strip().lower())
        if _too_similar(text_sim, image_sim, same_era):
            continue

        # Gate: simple average
        components = [text_sim, structural_score]
        if image_sim is not None:
            components.append(image_sim)
        if sum(components) / len(components) < min_bridge:
            continue

        lo, hi = min(product.id, cand_id), max(product.id, cand_id)
        shared['discovery'] = 'similarity'
        bridge = {
            'source_id': lo,
            'target_id': hi,
            'text_similarity': round(text_sim, 4),
            'image_similarity': round(image_sim, 4) if image_sim is not None else None,
            'structural_score': round(structural_score, 4),
            'shared_attributes': json.dumps(shared),
            'bridge_type': 'similarity',
            'created_at': datetime.now(tz=timezone.utc),
        }
        classify_bridge(product_map[lo], product_map[hi], bridge)
        bridges.append(bridge)

    return bridges


# ===========================================================================
# Pass 2: Opposition (axis pole cross-join, no boundary requirement)
# ===========================================================================

MAX_PER_SIDE = 200  # cap per pole side to limit O(n²) blowup

def run_opposition_pass(product_map, embedding_cache, existing_pairs,
                        structural_gate=0.35, top_per_pair=150, dry_run=False):
    """Find contrast bridges via opposing vibe axis poles."""
    print("\n  Pass 2: Opposition (axis pole cross-join)")

    products = list(product_map.values())
    vibe_index = build_vibe_index(products)

    total_candidates = 0
    total_passed_gate = 0
    product_appearances = {}
    max_appearances = 8

    all_pair_results = []

    for pole_a, pole_b, axis in OPPOSITION_PAIRS:
        ids_a = vibe_index.get(pole_a, set())
        ids_b = vibe_index.get(pole_b, set())
        if not ids_a or not ids_b:
            continue

        # Sample down large sides to avoid O(n²) blowup
        # Prefer products with richer cross-cultural fields
        def _subsample(ids, cap):
            if len(ids) <= cap:
                return ids
            scored = []
            for pid in ids:
                p = product_map[pid]
                richness = sum(1 for f in ('_construction_technique_set', '_social_function_set', '_motif_family_set')
                               if getattr(p, f, set()))
                scored.append((pid, richness))
            scored.sort(key=lambda x: -x[1])
            return {pid for pid, _ in scored[:cap]}

        ids_a = _subsample(ids_a, MAX_PER_SIDE)
        ids_b = _subsample(ids_b, MAX_PER_SIDE)

        pair_bridges = []
        for a_id in ids_a:
            for b_id in ids_b:
                if a_id == b_id:
                    continue
                lo, hi = min(a_id, b_id), max(a_id, b_id)
                if (lo, hi) in existing_pairs:
                    continue
                total_candidates += 1

                a = product_map[a_id]
                b = product_map[b_id]

                # Skip near-duplicates
                if (a.title and b.title
                    and a.title.strip().lower() == b.title.strip().lower()):
                    continue

                structural_score, shared = compute_structural_score(a, b)
                if structural_score < structural_gate:
                    continue
                total_passed_gate += 1

                text_a, img_a = embedding_cache.get(a_id, (None, None))
                text_b, img_b = embedding_cache.get(b_id, (None, None))
                text_sim = _cosine_sim(text_a, text_b) or 0.0
                image_sim = _cosine_sim(img_a, img_b)

                same_era = (a.era and b.era
                            and a.era.strip().lower() == b.era.strip().lower())
                if _too_similar(text_sim, image_sim, same_era):
                    continue

                shared['discovery'] = 'opposition'
                shared['opposition_pair'] = f"{pole_a} <-> {pole_b}"
                shared['axis'] = axis

                bridge = {
                    'source_id': lo,
                    'target_id': hi,
                    'text_similarity': round(text_sim, 4),
                    'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                    'structural_score': round(structural_score, 4),
                    'shared_attributes': json.dumps(shared),
                    'bridge_type': 'opposition',
                    'created_at': datetime.now(tz=timezone.utc),
                }
                # Inline classification
                classify_bridge(a, b, bridge)

                pair_bridges.append(bridge)

        # Composite sort: cross-cultural overlap + temporal distance + structural
        for b in pair_bridges:
            src = product_map[b['source_id']]
            tgt = product_map[b['target_id']]
            cc_score = 0.0
            for field, weight in [('_construction_technique_set', 0.14),
                                  ('_social_function_set', 0.12),
                                  ('_motif_family_set', 0.12)]:
                s_set = getattr(src, field, set())
                t_set = getattr(tgt, field, set())
                if s_set and t_set:
                    cc_score += weight * len(s_set & t_set) / len(s_set | t_set)
            cc_norm = cc_score / 0.38 if cc_score > 0 else 0.0

            gap = _get_year_gap(src, tgt)
            temporal_norm = min(gap / 200.0, 1.0) if gap is not None else 0.0

            b['_sort_score'] = (
                0.40 * cc_norm
              + 0.35 * temporal_norm
              + 0.25 * b['structural_score']
            )

        # Keep top N per pair with participation cap
        pair_bridges.sort(key=lambda b: b['_sort_score'], reverse=True)
        kept = []
        for b in pair_bridges:
            if len(kept) >= top_per_pair:
                break
            sid, tid = b['source_id'], b['target_id']
            if product_appearances.get(sid, 0) >= max_appearances:
                continue
            if product_appearances.get(tid, 0) >= max_appearances:
                continue
            del b['_sort_score']
            kept.append(b)
            product_appearances[sid] = product_appearances.get(sid, 0) + 1
            product_appearances[tid] = product_appearances.get(tid, 0) + 1
        all_pair_results.append((pole_a, pole_b, kept))

    # Batch insert
    all_bridges = []
    for _, _, kept in all_pair_results:
        all_bridges.extend(kept)
    if dry_run:
        for b in all_bridges:
            existing_pairs.add((b['source_id'], b['target_id']))
        total_inserted = len(all_bridges)
    else:
        total_inserted = _batch_insert_bridges(all_bridges, existing_pairs)

    for pole_a, pole_b, kept in all_pair_results:
        if kept:
            print(f"    {pole_a} <-> {pole_b}: {len(kept)} kept")

    print(f"    Total: {total_candidates} candidates, {total_passed_gate} passed gate, "
          f"{total_inserted} inserted")
    return total_inserted


# ===========================================================================
# Pass 3: Structural (shared form, cross-context only)
# ===========================================================================

def run_structural_pass(product_map, embedding_cache, existing_pairs,
                        min_structural=0.40, top_per_group=30,
                        discovery_bonus=0.10, bonus_threshold=0.4, dry_run=False):
    """Find structural doppelgangers — same shape, different context."""
    print("\n  Pass 3: Structural (category+silhouette grouping, cross-context)")

    products = list(product_map.values())
    groups = build_structural_groups(products)
    print(f"    {len(groups)} structural groups (category+silhouette, >=3 products)")

    all_group_results = []
    product_appearances = {}
    max_appearances = 8

    for (cat, sil), prod_ids in sorted(groups.items(), key=lambda x: -len(x[1])):
        group_bridges = []
        id_list = sorted(prod_ids)
        if len(id_list) > 100:
            def cross_cultural_richness(pid):
                p = product_map[pid]
                count = 0
                for f in ('_construction_technique_set', '_social_function_set', '_motif_family_set'):
                    if getattr(p, f, set()):
                        count += 1
                return count
            id_list.sort(key=cross_cultural_richness, reverse=True)
            id_list = id_list[:100]
            id_list.sort()

        for i, a_id in enumerate(id_list):
            for b_id in id_list[i+1:]:
                lo, hi = a_id, b_id
                if (lo, hi) in existing_pairs:
                    continue

                a = product_map[a_id]
                b = product_map[b_id]

                if (a.title and b.title
                    and a.title.strip().lower() == b.title.strip().lower()):
                    continue

                # Must cross boundary (20+ yr gap OR different culture)
                if not _crosses_boundary(a, b):
                    continue

                structural_score, shared = compute_structural_score(a, b)
                if structural_score < min_structural:
                    continue

                text_a, img_a = embedding_cache.get(a_id, (None, None))
                text_b, img_b = embedding_cache.get(b_id, (None, None))
                text_sim = _cosine_sim(text_a, text_b) or 0.0
                image_sim = _cosine_sim(img_a, img_b)

                same_era = (a.era and b.era
                            and a.era.strip().lower() == b.era.strip().lower())
                if _too_similar(text_sim, image_sim, same_era):
                    continue

                bonus = discovery_bonus if text_sim < bonus_threshold else 0.0
                sort_score = structural_score + bonus

                shared['discovery'] = 'structural_parallel'
                if bonus > 0:
                    shared['independent_invention'] = True

                bridge = {
                    'source_id': lo,
                    'target_id': hi,
                    'text_similarity': round(text_sim, 4),
                    'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                    'structural_score': round(structural_score, 4),
                    'shared_attributes': json.dumps(shared),
                    'bridge_type': 'structural',
                    'created_at': datetime.now(tz=timezone.utc),
                    '_sort_score': sort_score,
                }
                classify_bridge(a, b, bridge)
                group_bridges.append(bridge)

        group_bridges.sort(key=lambda b: b['_sort_score'], reverse=True)
        kept = []
        for b in group_bridges:
            if len(kept) >= top_per_group:
                break
            sid, tid = b['source_id'], b['target_id']
            if product_appearances.get(sid, 0) >= max_appearances:
                continue
            if product_appearances.get(tid, 0) >= max_appearances:
                continue
            del b['_sort_score']
            kept.append(b)
            product_appearances[sid] = product_appearances.get(sid, 0) + 1
            product_appearances[tid] = product_appearances.get(tid, 0) + 1
        all_group_results.append((cat, sil, kept))

    all_bridges = []
    for _, _, kept in all_group_results:
        all_bridges.extend(kept)

    if dry_run:
        for b in all_bridges:
            existing_pairs.add((b['source_id'], b['target_id']))
        total_inserted = len(all_bridges)
    else:
        total_inserted = _batch_insert_bridges(all_bridges, existing_pairs)

    for cat, sil, kept in all_group_results:
        if kept:
            print(f"    {cat}/{sil}: {len(kept)} kept")

    print(f"    Total inserted: {total_inserted}")
    return total_inserted


# ===========================================================================
# Pass 4: Visual Echo (image similarity, cross-time AND cross-culture)
# ===========================================================================

VISUAL_ECHO_YEAR_GAP = 40  # stricter than boundary: must be far apart in time

def run_visual_echo_pass(product_map, image_ids, embedding_cache, existing_pairs,
                         top_k=15, top_per_product=3,
                         dry_run=False):
    """Find bridges where garments look alike across time OR culture.
    Image-only pgvector search, boundary: 40+ year gap OR different culture."""
    print("\n  Pass 4: Visual Echo (image similarity, cross-time or cross-culture)")

    # Only products with image embeddings
    eligible = [p for pid, p in product_map.items() if pid in image_ids]
    print(f"    {len(eligible)} products with image embeddings")

    if not eligible:
        print("    No image-embedded products. Skipping.")
        return 0

    product_appearances = {}
    max_appearances = 6  # tighter cap — visual echo should be selective
    total_inserted = 0
    batch_bridges = []
    total_candidates = 0

    db = SessionLocal()
    FLUSH_EVERY = 200  # insert bridges and refresh DB connection every N products

    for i, product in enumerate(eligible):
        # Get image embedding from cache (no DB round-trip)
        _, img_vec = embedding_cache.get(product.id, (None, None))
        if img_vec is None:
            continue
        params = {
            "pid": product.id,
            "top_k": top_k,
            "img_vec": img_vec if isinstance(img_vec, str) else str(list(img_vec)),
        }

        candidates = db.execute(text("""
            SELECT id, 1 - (image_embedding <=> :img_vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL AND id != :pid
            ORDER BY image_embedding <=> :img_vec
            LIMIT :top_k
        """), params).fetchall()

        kept = 0
        for cand_id, image_sim in candidates:
            if kept >= top_per_product:
                break

            target = product_map.get(cand_id)
            if target is None:
                continue

            lo, hi = min(product.id, cand_id), max(product.id, cand_id)
            if (lo, hi) in existing_pairs:
                continue

            # Skip near-duplicates
            if (product.title and target.title
                    and product.title.strip().lower() == target.title.strip().lower()):
                continue

            # Must cross time (40+ yr) OR culture
            gap = _get_year_gap(product, target)
            crosses_time = gap is not None and gap >= VISUAL_ECHO_YEAR_GAP
            src_culture = (product.culture or '').strip().lower()
            tgt_culture = (target.culture or '').strip().lower()
            crosses_culture = src_culture and tgt_culture and src_culture != tgt_culture
            if not crosses_time and not crosses_culture:
                continue

            structural_score, shared = compute_structural_score(product, target)

            # Text similarity from embedding cache (no DB round-trip)
            text_a, _ = embedding_cache.get(product.id, (None, None))
            text_b, _ = embedding_cache.get(cand_id, (None, None))
            text_sim = _cosine_sim(text_a, text_b) or 0.0

            same_era = (product.era and target.era
                        and product.era.strip().lower() == target.era.strip().lower())
            if _too_similar(text_sim, image_sim, same_era):
                continue

            # Participation cap
            if product_appearances.get(lo, 0) >= max_appearances:
                continue
            if product_appearances.get(hi, 0) >= max_appearances:
                continue

            shared['discovery'] = 'visual_echo'

            bridge = {
                'source_id': lo,
                'target_id': hi,
                'text_similarity': round(text_sim, 4),
                'image_similarity': round(float(image_sim), 4),
                'structural_score': round(structural_score, 4),
                'shared_attributes': json.dumps(shared),
                'bridge_type': 'visual_echo',
                'created_at': datetime.now(tz=timezone.utc),
            }
            classify_bridge(product_map[lo], product_map[hi], bridge)
            batch_bridges.append(bridge)

            product_appearances[lo] = product_appearances.get(lo, 0) + 1
            product_appearances[hi] = product_appearances.get(hi, 0) + 1
            kept += 1

        # Flush batch and refresh connection periodically
        if (i + 1) % FLUSH_EVERY == 0:
            if batch_bridges and not dry_run:
                total_inserted += _batch_insert_bridges(batch_bridges, existing_pairs)
            elif dry_run:
                for b in batch_bridges:
                    existing_pairs.add((b['source_id'], b['target_id']))
                total_inserted += len(batch_bridges)
            total_candidates += len(batch_bridges)
            batch_bridges = []
            # Refresh DB connection to avoid pooler timeout
            try:
                db.close()
            except Exception:
                pass
            db = SessionLocal()
            print(f"    [{i+1}/{len(eligible)}] {total_candidates} candidates, {total_inserted} inserted")

    # Flush remaining
    if batch_bridges:
        if not dry_run:
            total_inserted += _batch_insert_bridges(batch_bridges, existing_pairs)
        else:
            for b in batch_bridges:
                existing_pairs.add((b['source_id'], b['target_id']))
            total_inserted += len(batch_bridges)
        total_candidates += len(batch_bridges)

    db.close()

    print(f"    Total: {total_candidates} candidates, {total_inserted} inserted")
    return total_inserted


# ===========================================================================
# Main pipeline
# ===========================================================================

def compute_bridges(rebuild=False, limit=None,
                    top_k=20, top_n=5,
                    min_structural_open=0.30,
                    min_bridge=0.40,
                    start_pass=1,
                    dry_run=False):
    """
    Compute style bridges with four passes + inline classification:
      1. Similarity    — vector proximity, cross-context only
      2. Opposition    — vibe axis pole cross-join, no boundary req
      3. Structural    — shared (category, silhouette), cross-context only
      4. Visual Echo   — image similarity, 40+ yr gap or cross-culture
    """
    # --- Load products ---
    _db = SessionLocal()
    products = _db.query(Product).filter(Product.enriched_at != None).all()
    product_map = {p.id: p for p in products}
    for p in products:
        _ = p.vibe_scores, p.social_function, p.construction_technique, p.motif_family
        _ = p.culture, p.era, p.decade, p.fp_category, p.silhouette, p.platform
        _ = p.title, p.designer
        _ = p.nickname, p.neckline, p.length, p.waistline, p.sleeve_length
        _ = p.textile_pattern, p.opening_type
        _ = p.influence_references, p.named_movements, p.garment_system
        _ = p.garment_parts, p.decorations, p.textile_finishing
        _db.expunge(p)
    _db.close()
    preparse_set_fields(product_map)

    # --- Check embeddings ---
    _db = SessionLocal()
    text_ids, image_ids = get_embedded_ids(_db)
    _db.close()

    print("\n" + "=" * 70)
    print("COMPUTING STYLE BRIDGES")
    print("  4 passes: similarity | opposition | structural | visual echo")
    print("  Inline classification: temporal + crossing + connection mode")
    print("=" * 70)

    eligible = [p for p in products if p.id in text_ids]
    if limit:
        eligible = eligible[:limit]
        # Build a limited product map for passes 2-4 (controls which products
        # are used as sources, but full product_map is kept for target lookups)
        limited_ids = {p.id for p in eligible}
        limited_product_map = {pid: p for pid, p in product_map.items() if pid in limited_ids}
        limited_image_ids = image_ids & limited_ids
    else:
        limited_product_map = product_map
        limited_image_ids = image_ids

    by_platform = {}
    for p in eligible:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print(f"\n  Enriched products:       {len(products)}")
    print(f"  Text-embedded (pgvector):  {len(text_ids)}")
    print(f"  Image-embedded (pgvector): {len(image_ids)}")
    print(f"  Eligible for bridging:   {len(eligible)}")
    print(f"\n  By platform:")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {platform:20s} {count:4d}")

    if not eligible:
        print("\n  No eligible products.")
        return

    if rebuild and not dry_run:
        _db = SessionLocal()
        deleted = _db.query(StyleBridge).delete()
        _db.commit()
        _db.close()
        print(f"\n  Cleared {deleted} existing bridges.")

    # Resume tracking
    already_bridged = set()
    if not rebuild:
        db = SessionLocal()
        rows = db.execute(
            text("SELECT DISTINCT source_id FROM style_bridges")
        ).fetchall()
        already_bridged = {r[0] for r in rows}
        db.close()

    if start_pass > 1:
        print(f"\n  Skipping to pass {start_pass}")

    print(f"\n  Parameters: top_k={top_k}  min_structural={min_structural_open}  "
          f"min_bridge={min_bridge}  boundary_gap={BOUNDARY_YEAR_GAP}yr"
          f"{'  DRY RUN' if dry_run else ''}")
    print("\n" + "-" * 70)

    total_stored = 0
    existing_pairs = set()
    embedding_cache = {}
    start_time = time.time()

    if not rebuild:
        db = SessionLocal()
        rows = db.execute(
            text("SELECT source_id, target_id FROM style_bridges")
        ).fetchall()
        existing_pairs = {(r[0], r[1]) for r in rows}
        if existing_pairs:
            print(f"  Loaded {len(existing_pairs)} existing pairs for dedup")
        db.close()

    # --- Pass 1: Similarity ---
    if start_pass <= 1:
        print(f"\n  Pass 1: Similarity (vector proximity, cross-context)")
        db = SessionLocal()
        pass1_count = 0
        skipped_resume = 0
        pass1_appearances = {}  # participation cap
        max_appearances_pass1 = 8

        for i, product in enumerate(eligible):
            if product.id in already_bridged:
                skipped_resume += 1
                continue

            text_vector, image_vector = _get_embeddings(db, product.id, embedding_cache)
            if text_vector is None:
                continue

            candidates = search_candidates_pgvector(
                db, product.id, text_vector, image_vector, top_k)

            bridges = score_and_filter_candidates(
                product, candidates, product_map,
                min_structural_open, min_bridge)

            # Keep top N
            bridges.sort(
                key=lambda b: (b['text_similarity'] + (b['image_similarity'] or 0) + b['structural_score'])
                    / (3 if b['image_similarity'] is not None else 2),
                reverse=True)
            bridges = bridges[:top_n]

            product_bridges = 0
            for b in bridges:
                if b['source_id'] == b['target_id']:
                    continue
                sid, tid = b['source_id'], b['target_id']
                if pass1_appearances.get(sid, 0) >= max_appearances_pass1:
                    continue
                if pass1_appearances.get(tid, 0) >= max_appearances_pass1:
                    continue
                if dry_run:
                    pair = (sid, tid)
                    if pair not in existing_pairs:
                        existing_pairs.add(pair)
                        product_bridges += 1
                        pass1_appearances[sid] = pass1_appearances.get(sid, 0) + 1
                        pass1_appearances[tid] = pass1_appearances.get(tid, 0) + 1
                else:
                    if _insert_bridge(db, b, existing_pairs):
                        product_bridges += 1
                        pass1_appearances[sid] = pass1_appearances.get(sid, 0) + 1
                        pass1_appearances[tid] = pass1_appearances.get(tid, 0) + 1

            pass1_count += product_bridges
            if product_bridges and not dry_run:
                db.commit()

            if (i + 1) % 25 == 0 or (i + 1) == len(eligible):
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(eligible) - i - 1) / rate if rate > 0 else 0
                print(f"    [{i+1:4d}/{len(eligible)}]  "
                      f"{pass1_count:5d} bridges  "
                      f"{rate:.1f} items/s  "
                      f"ETA {eta:.0f}s")

        db.commit()
        total_stored += pass1_count
        print(f"\n  Pass 1 complete: {pass1_count} bridges")
    else:
        print(f"  Pass 1: skipped (start_pass={start_pass})")

    # --- Passes 2-4: non-vector candidate selection ---
    print("\n" + "-" * 70)
    print("Running passes 2-4 (opposition, structural, visual echo)...\n")
    print(f"  {len(existing_pairs)} existing bridge pairs tracked for dedup")

    engine.dispose()
    _db = SessionLocal()
    embedding_cache = bulk_load_embeddings(_db)
    _db.close()

    if start_pass <= 2:
        opposition_count = run_opposition_pass(limited_product_map, embedding_cache, existing_pairs, dry_run=dry_run)
        total_stored += opposition_count
    else:
        print(f"  Pass 2: skipped (start_pass={start_pass})")

    if start_pass <= 3:
        structural_count = run_structural_pass(limited_product_map, embedding_cache, existing_pairs, dry_run=dry_run)
        total_stored += structural_count
    else:
        print(f"  Pass 3: skipped (start_pass={start_pass})")

    visual_count = run_visual_echo_pass(limited_product_map, limited_image_ids, embedding_cache, existing_pairs, dry_run=dry_run)
    total_stored += visual_count

    elapsed = time.time() - start_time

    # --- Summary ---
    print("\n" + "=" * 70)
    label = "DRY RUN COMPLETE" if dry_run else "BRIDGE COMPUTATION COMPLETE"
    print(f"{label} — {total_stored} bridges {'would be created' if dry_run else 'created'} in {elapsed:.1f}s")
    print("=" * 70)

    if not dry_run:
        db = SessionLocal()
        total = db.query(func.count(StyleBridge.id)).scalar()

        print(f"\n  PASS (which discovery method)")
        for row in db.query(StyleBridge.bridge_type, func.count()).group_by(
                StyleBridge.bridge_type).order_by(func.count().desc()).all():
            pct = 100 * row[1] / total if total else 0
            print(f"    {row[0] or 'NULL':20s} {row[1]:>6}  ({pct:.0f}%)")

        print(f"\n  TIME (year gap distribution)")
        gap_buckets = db.execute(text('''
            SELECT
                CASE
                    WHEN year_gap IS NULL THEN 'unknown'
                    WHEN year_gap < 20 THEN 'contemporary (<20yr)'
                    WHEN year_gap < 40 THEN 'continuation (20-39yr)'
                    WHEN year_gap < 80 THEN 'transmission (40-79yr)'
                    ELSE 'echo (80+yr)'
                END as bucket,
                count(*)
            FROM style_bridges GROUP BY bucket ORDER BY count(*) DESC
        ''')).fetchall()
        for bucket, cnt in gap_buckets:
            pct = 100 * cnt / total if total else 0
            print(f"    {bucket:25s} {cnt:>6}  ({pct:.0f}%)")

        print(f"\n  CONTEXT (what boundary was crossed)")
        for row in db.query(StyleBridge.crossing_type, func.count()).group_by(
                StyleBridge.crossing_type).order_by(func.count().desc()).all():
            pct = 100 * row[1] / total if total else 0
            print(f"    {row[0] or 'NULL':30s} {row[1]:>6}  ({pct:.0f}%)")

        print(f"\n  CONNECTION (aesthetic relationship)")
        for row in db.query(StyleBridge.connection_mode, func.count()).group_by(
                StyleBridge.connection_mode).order_by(func.count().desc()).all():
            pct = 100 * row[1] / total if total else 0
            print(f"    {row[0] or 'NULL':20s} {row[1]:>6}  ({pct:.0f}%)")

        print(f"\n  AXIS (design dimension)")
        for row in db.query(StyleBridge.primary_axis, func.count()).group_by(
                StyleBridge.primary_axis).order_by(func.count().desc()).all():
            pct = 100 * row[1] / total if total else 0
            print(f"    {row[0] or 'NULL':20s} {row[1]:>6}  ({pct:.0f}%)")

        contrasts = db.query(StyleBridge.contrast_pair, func.count()).filter(
            StyleBridge.contrast_pair != None
        ).group_by(StyleBridge.contrast_pair).all()
        if contrasts:
            print(f"\n  CONTRAST PAIRS")
            for row in sorted(contrasts, key=lambda x: -x[1]):
                print(f"    {row[0]:50s} {row[1]:>6}")

        # KG bridge fields
        kg_stats = db.execute(text('''
            SELECT
                count(*) FILTER (WHERE shared_designer IS NOT NULL) as designers,
                count(*) FILTER (WHERE shared_movements IS NOT NULL) as movements,
                count(*) FILTER (WHERE shared_influences IS NOT NULL) as influences
            FROM style_bridges
        ''')).fetchone()
        print(f"\n  KG BRIDGE FIELDS")
        print(f"    Shared designer:    {kg_stats[0]:>6}")
        print(f"    Shared movements:   {kg_stats[1]:>6}")
        print(f"    Shared influences:  {kg_stats[2]:>6}")

        # Bridge score distribution
        score_stats = db.execute(text('''
            SELECT round(avg(bridge_score)::numeric, 3),
                   round(min(bridge_score)::numeric, 3),
                   round(max(bridge_score)::numeric, 3)
            FROM style_bridges
        ''')).fetchone()
        print(f"\n  BRIDGE SCORE")
        print(f"    avg={score_stats[0]}  min={score_stats[1]}  max={score_stats[2]}")

        db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compute style bridges (4 passes + inline classification)')
    parser.add_argument('--rebuild', action='store_true', help='Delete all bridges and recompute')
    parser.add_argument('--dry-run', action='store_true', help='Calculate bridges without writing to DB')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of products')
    parser.add_argument('--start-pass', type=int, default=1, help='Start from pass N (1-4)')
    args = parser.parse_args()
    compute_bridges(rebuild=args.rebuild, limit=args.limit, start_pass=args.start_pass, dry_run=args.dry_run)
