"""
Compute style bridges between enriched products.

Four discovery passes, each using a different candidate selection strategy:
  1. Similarity     — vector proximity (pgvector), finds affinity/resonance bridges
  2. Opposition     — opposing core_vibes cross-join, finds contrast bridges
  3. Shared Purpose — shared social_function grouping, finds cross-cultural comparison bridges
  4. Parallel Form  — shared (category, silhouette) grouping, finds independent invention bridges

Bridge types stored per pass:
  transmission / continuation / cross_vibe  (Pass 1, temporal classification)
  opposition                                (Pass 2)
  function                                  (Pass 3)
  structural                                (Pass 4)

Usage:
  python analysis/compute_bridges.py [--rebuild] [--limit=N]

Run from project root.
"""

import sys
import os
import json
import time
import numpy as np
from datetime import datetime, timezone

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product, StyleBridge
from enrichment.era_taxonomy import ERAS
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func, text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HISTORICAL_PLATFORMS = {'met_museum', 'smithsonian'}
MODERN_PLATFORMS = {'fashionpedia'}

# Continuation: minimum year distance for same-era items to qualify
CONTINUATION_DISTANCE = 20

# Transmission: minimum year distance between era midpoints to qualify
TRANSMISSION_DISTANCE = 40

# Pre-compute era midpoints for distance checks
_ERA_MIDPOINTS = {}
for _name, _data in ERAS.items():
    _ERA_MIDPOINTS[_name.strip().lower()] = (_data['start'] + _data['end']) // 2

# Structural field weights
# Redistributed to include cross-cultural bridge fields (2026-03-06)
STRUCTURAL_WEIGHTS = {
    'fp_category':              0.16,
    'silhouette':               0.12,
    'nickname':                 0.08,
    'neckline':                 0.07,
    'length':                   0.07,
    'waistline':                0.06,
    'sleeve_length':            0.05,
    'textile_pattern':          0.04,
    'opening_type':             0.03,
    'garment_parts':            0.04,   # Jaccard
    'decorations':              0.02,   # Jaccard
    'textile_finishing':        0.02,   # Jaccard
    # Cross-cultural bridge fields
    'construction_technique':   0.10,   # Jaccard — e.g. resist-dyeing, hand-embroidery
    'social_function':          0.07,   # Jaccard — e.g. ["wedding", "status-signaling"]
    'motif_family':             0.07,   # Jaccard — e.g. geometric, paisley, floral
}

SET_FIELDS = {'garment_parts', 'decorations', 'textile_finishing', 'construction_technique', 'social_function', 'motif_family'}

# Opposition pairs: (vibe_a, vibe_b, axis) — used by _vibes_diverge and run_opposition_pass
OPPOSITION_PAIRS = [
    ("Exaggerated Volume",          "Column Minimalism",          "volume"),
    ("Constructed Armor",           "Draped Fluidity",            "volume"),
    ("Constructed Armor",           "Body Liberation",            "volume"),
    ("Maximalist Ornament",         "Austere Restraint",          "ornament"),
    ("Transparency and Revelation", "Body Concealment",           "ornament"),
    ("Body Liberation",             "Body Transformation",        "body"),
    ("Body Display",                "Body Concealment",           "body"),
    ("Transgressive Subversion",    "Elite Distinction",          "register"),
    ("Pastoral Naturalism",         "Ceremonial Formalism",       "register"),
]


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


def parse_decade_to_year(decade: str | None) -> int | None:
    """Parse a decade string like '1870s' to its midpoint year (1875)."""
    if not decade:
        return None
    d = decade.strip().rstrip('s')
    try:
        return int(d) + 5
    except ValueError:
        return None


def classify_temporal_type(source_era, target_era,
                           source_platform, target_platform,
                           source_decade=None, target_decade=None) -> str:
    """Classify temporal relationship between two products.

    Returns:
      'echo' — different named eras, midpoints 80+ years apart
      'transmission' — different named eras, midpoints 40-79 years apart
      'continuation' — same era, decades 20+ years apart
      'contemporary' — same era, close decades (or not enough data)
    """

    if source_era and target_era:
        if source_era.strip().lower() != target_era.strip().lower():
            src_mid = _ERA_MIDPOINTS.get(source_era.strip().lower())
            tgt_mid = _ERA_MIDPOINTS.get(target_era.strip().lower())
            if src_mid is not None and tgt_mid is not None:
                gap = abs(src_mid - tgt_mid)
                if gap < TRANSMISSION_DISTANCE:
                    return 'contemporary'
                if gap >= 80:
                    return 'echo'
            return 'transmission'
        # Same era
        src_yr = parse_decade_to_year(source_decade)
        tgt_yr = parse_decade_to_year(target_decade)
        if src_yr and tgt_yr and abs(src_yr - tgt_yr) >= CONTINUATION_DISTANCE:
            return 'continuation'
        return 'contemporary'

    # Fallback: platform as temporal proxy
    s_hist = source_platform in HISTORICAL_PLATFORMS
    t_hist = target_platform in HISTORICAL_PLATFORMS
    if s_hist != t_hist:
        return 'transmission'
    return 'contemporary'


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def get_embedded_ids(db):
    """Get sets of product IDs that have text/image embeddings."""
    text_ids = {r[0] for r in db.execute(
        text("SELECT id FROM products WHERE text_embedding IS NOT NULL")
    ).fetchall()}

    image_ids = {r[0] for r in db.execute(
        text("SELECT id FROM products WHERE image_embedding IS NOT NULL")
    ).fetchall()}

    return text_ids, image_ids


# ---------------------------------------------------------------------------
# Filter builders
# ---------------------------------------------------------------------------

def build_open_filter(product):
    """No extra restrictions."""
    return "", {}


CATEGORY_GROUPS = {
    'tops':      {'blouse', 'shirt', 'top', 't-shirt', 'sweater', 'tank top', 'camisole', 'bodysuit'},
    'outerwear': {'coat', 'jacket', 'blazer', 'cape', 'vest', 'cardigan', 'poncho', 'parka'},
    'bottoms':   {'pants', 'shorts', 'trousers', 'jeans', 'leggings', 'culottes'},
    'dresses':   {'dress', 'gown', 'robe', 'jumpsuit', 'romper'},
    'skirts':    {'skirt', 'mini skirt', 'maxi skirt'},
}

# Reverse lookup: category -> group name
_CAT_TO_GROUP = {}
for group, cats in CATEGORY_GROUPS.items():
    for cat in cats:
        _CAT_TO_GROUP[cat] = group

CROSS_CULTURAL_FIELDS = {'construction_technique', 'social_function', 'motif_family'}


def _get_category_group(fp_category):
    """Return the group name for an fp_category, or the category itself if ungrouped."""
    if not fp_category:
        return None
    return _CAT_TO_GROUP.get(fp_category.strip().lower(), fp_category.strip().lower())


def _parse_vibes(product) -> set:
    """Extract core_vibes as a set from a product's JSON field."""
    raw = getattr(product, 'core_vibes', None)
    if not raw:
        return set()
    try:
        vibes = json.loads(raw) if isinstance(raw, str) else raw
        return set(vibes) if vibes else set()
    except (json.JSONDecodeError, TypeError):
        return set()


def _vibes_diverge(source, target) -> bool:
    """Check if two products have sufficiently different core_vibes.

    Returns True if:
      - Vibes have zero overlap (completely different arguments), OR
      - Vibes contain an opposition pair from the controlled vocabulary
    """
    src_vibes = _parse_vibes(source)
    tgt_vibes = _parse_vibes(target)

    if not src_vibes or not tgt_vibes:
        return False

    # Zero overlap = divergent
    if not src_vibes & tgt_vibes:
        return True

    # Check for opposition pairs (module-level OPPOSITION_PAIRS)
    for vibe_a, vibe_b, _axis in OPPOSITION_PAIRS:
        if (vibe_a in src_vibes and vibe_b in tgt_vibes) or \
           (vibe_b in src_vibes and vibe_a in tgt_vibes):
            return True

    return False


def shares_cross_cultural_field(source, target):
    """Check if two products share at least one value in any cross-cultural field."""
    for field in CROSS_CULTURAL_FIELDS:
        s_val = getattr(source, field, None)
        t_val = getattr(target, field, None)
        if not s_val or not t_val:
            continue
        try:
            s_set = set(json.loads(s_val)) if isinstance(s_val, str) else set(s_val)
            t_set = set(json.loads(t_val)) if isinstance(t_val, str) else set(t_val)
        except (json.JSONDecodeError, TypeError):
            continue
        # Remove 'none' values
        s_set.discard('none')
        t_set.discard('none')
        if s_set & t_set:
            return True
    return False


def build_cross_category_filter(product):
    """Exclude same category GROUP (not just exact match). Returns (None, None) if no category."""
    if not product.fp_category:
        return None, None
    group = _get_category_group(product.fp_category)
    # Get all categories in the same group to exclude
    group_cats = CATEGORY_GROUPS.get(group)
    if group_cats:
        # Exclude the entire group via SQL
        placeholders = ", ".join(f":excl_cat_{i}" for i in range(len(group_cats)))
        params = {f"excl_cat_{i}": cat for i, cat in enumerate(group_cats)}
        return f"AND LOWER(fp_category) NOT IN ({placeholders})", params
    # Ungrouped category — just exclude exact match
    return "AND LOWER(fp_category) != :excl_cat", {"excl_cat": product.fp_category.strip().lower()}


def build_cross_culture_filter(product):
    """Exclude same culture. Returns (None, None) if no culture."""
    if not product.culture:
        return None, None
    return "AND culture != :excl_culture", {"excl_culture": product.culture}


# ---------------------------------------------------------------------------
# Embedding helpers for passes 2-4 (no vector search, need sim for scoring)
# ---------------------------------------------------------------------------

def _get_embeddings(db, product_id, cache):
    """Lazy-load and cache embeddings for a product."""
    if product_id not in cache:
        row = db.execute(
            text("SELECT text_embedding, image_embedding FROM products WHERE id = :id"),
            {"id": product_id}
        ).fetchone()
        cache[product_id] = (row[0], row[1]) if row else (None, None)
    return cache[product_id]


def _cosine_sim(vec_a, vec_b):
    """Cosine similarity between two pgvector strings or arrays."""
    if vec_a is None or vec_b is None:
        return None
    a = np.array(json.loads(vec_a) if isinstance(vec_a, str) else list(vec_a), dtype=np.float32)
    b = np.array(json.loads(vec_b) if isinstance(vec_b, str) else list(vec_b), dtype=np.float32)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def _insert_bridge(db, bridge_dict, existing_pairs):
    """Insert with ON CONFLICT DO NOTHING. Returns True if inserted."""
    pair = (bridge_dict['source_id'], bridge_dict['target_id'])
    if pair in existing_pairs:
        return False
    stmt = pg_insert(StyleBridge.__table__).values(**bridge_dict)
    stmt = stmt.on_conflict_do_nothing(constraint='uq_bridge_pair')
    result = db.execute(stmt)
    if result.rowcount:
        existing_pairs.add(pair)
        return True
    return False


# ---------------------------------------------------------------------------
# Index builders for passes 2-4
# ---------------------------------------------------------------------------

def build_vibe_index(products):
    """Map each vibe term to the set of product IDs that have it."""
    index = {}
    for p in products:
        vibes = _parse_vibes(p)
        for v in vibes:
            index.setdefault(v, set()).add(p.id)
    return index


def build_function_index(products):
    """Map each social_function value to the set of product IDs."""
    index = {}
    for p in products:
        raw = getattr(p, 'social_function', None)
        if not raw:
            continue
        try:
            funcs = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        for f in (funcs or []):
            if f and f != 'none':
                index.setdefault(f, set()).add(p.id)
    return index


def build_structural_groups(products):
    """Group products by (fp_category_group, silhouette). Skip groups < 3."""
    groups = {}
    for p in products:
        cat = _get_category_group(p.fp_category)
        sil = (p.silhouette or '').strip().lower()
        if cat and sil:
            groups.setdefault((cat, sil), set()).add(p.id)
    return {k: v for k, v in groups.items() if len(v) >= 3}


# ---------------------------------------------------------------------------
# Search + score helpers
# ---------------------------------------------------------------------------

def search_candidates_pgvector(db, product_id, text_vector, image_vector, exclude_sql, exclude_params, top_k):
    """Search for bridge candidates using pgvector."""
    candidates = {}
    params = {"pid": product_id, "top_k": top_k, **exclude_params}

    if text_vector is not None:
        params["text_vec"] = text_vector if isinstance(text_vector, str) else str(list(text_vector))
        rows = db.execute(text(f"""
            SELECT id, 1 - (text_embedding <=> :text_vec) as score
            FROM products
            WHERE text_embedding IS NOT NULL
              AND id != :pid
              {exclude_sql}
            ORDER BY text_embedding <=> :text_vec
            LIMIT :top_k                   
        """), params).fetchall()
        for row in rows:
            candidates[row[0]] = {'text_score': row[1], 'image_score': None}

    if image_vector is not None:
        params["img_vec"] = image_vector if isinstance(image_vector, str) else str(list(image_vector))
        rows = db.execute(text(f"""
            SELECT id, 1 - (image_embedding <=> :img_vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL
              AND id != :pid
              {exclude_sql}
            ORDER BY image_embedding <=> :img_vec
            LIMIT :top_k
        """), params).fetchall()
        for row in rows:
            if row[0] in candidates:
                candidates[row[0]]['image_score'] = row[1]
            else:
                candidates[row[0]] = {'text_score': None, 'image_score': row[1]}

    return candidates


def score_candidates(product, candidates, product_map,
                     min_structural, min_bridge, bridge_type_override=None,
                     pass_name=None):
    """
    Score candidates against a product. Returns (bridges_list, stats_dict).
    """
    bridges = []
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

        # Cross-category and cross-culture require shared cross-cultural field for substance
        if pass_name in ('cross_category', 'cross_culture') and not shares_cross_cultural_field(product, target):
            stats['skipped_structural'] += 1
            continue

        structural_score, shared = compute_structural_score(product, target)
        if structural_score < min_structural:
            stats['skipped_structural'] += 1
            continue

        text_sim = scores['text_score'] or 0.0
        image_sim = scores['image_score']

        # Gate: simple average of available component scores
        components = [text_sim, structural_score]
        if image_sim is not None:
            components.append(image_sim)
        gate_score = sum(components) / len(components)

        if gate_score < min_bridge:
            stats['skipped_bridge'] += 1
            continue

        # Skip items that share both category group AND era — unless vibes diverge.
        # "Two Victorian dresses" is boring. "Two Victorian dresses arguing about volume" is not.
        same_era = (product.era and target.era
                    and product.era.strip().lower() == target.era.strip().lower())
        same_cat_group = (product.fp_category and target.fp_category
                         and _get_category_group(product.fp_category) == _get_category_group(target.fp_category))
        if same_era and same_cat_group and not _vibes_diverge(product, target):
            stats['skipped_structural'] += 1
            continue

        if bridge_type_override:
            bridge_type = bridge_type_override
        else:
            bridge_type = classify_temporal_type(
                product.era, target.era,
                product.platform, target.platform,
                product.decade, target.decade,
            )
            if bridge_type is 'contemporary':
                # Same era, close decades — only keep if vibes diverge enough
                if _vibes_diverge(product, target):
                    bridge_type = 'cross_vibe'
                else:
                    stats['skipped_structural'] += 1
                    continue

        # Canonical ordering: always store min(id) -> max(id) so the
        # unique constraint catches the reverse direction automatically.
        lo, hi = min(product.id, cand_id), max(product.id, cand_id)

        bridges.append({
            'source_id': lo,
            'target_id': hi,
            'text_similarity': round(text_sim, 4),
            'image_similarity': round(image_sim, 4) if image_sim is not None else None,
            'structural_score': round(structural_score, 4),
            'shared_attributes': json.dumps(shared),
            'bridge_type': bridge_type,
            'created_at': datetime.now(tz=timezone.utc),
        })

    return bridges, stats


# ---------------------------------------------------------------------------
# Pass 2: Opposition (vibe-first)
# ---------------------------------------------------------------------------

def run_opposition_pass(db, product_map, embedding_cache, existing_pairs,
                        structural_gate=0.30, top_per_pair=20):
    """Find contrast bridges via opposing core_vibes cross-join.
    No vector search — candidates come from vibe opposition pairs."""
    print("\n  Pass 2: Opposition (vibe cross-join)")

    products = list(product_map.values())
    vibe_index = build_vibe_index(products)

    total_inserted = 0
    total_candidates = 0
    total_passed_gate = 0

    for vibe_a, vibe_b, axis in OPPOSITION_PAIRS:
        ids_a = vibe_index.get(vibe_a, set())
        ids_b = vibe_index.get(vibe_b, set())
        if not ids_a or not ids_b:
            continue

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
                structural_score, shared = compute_structural_score(a, b)
                if structural_score < structural_gate:
                    continue
                total_passed_gate += 1

                text_a, img_a = _get_embeddings(db, a_id, embedding_cache)
                text_b, img_b = _get_embeddings(db, b_id, embedding_cache)
                text_sim = _cosine_sim(text_a, text_b) or 0.0
                image_sim = _cosine_sim(img_a, img_b)

                shared['discovery'] = 'opposition'
                shared['opposition_pair'] = f"{vibe_a} <-> {vibe_b}"
                shared['axis'] = axis

                pair_bridges.append({
                    'source_id': lo,
                    'target_id': hi,
                    'text_similarity': round(text_sim, 4),
                    'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                    'structural_score': round(structural_score, 4),
                    'shared_attributes': json.dumps(shared),
                    'bridge_type': 'opposition',
                    'created_at': datetime.now(tz=timezone.utc),
                })

        # Keep top N per pair, sorted by structural (dominates for contrast)
        pair_bridges.sort(key=lambda b: b['structural_score'], reverse=True)
        inserted_this_pair = 0
        for b in pair_bridges[:top_per_pair]:
            if _insert_bridge(db, b, existing_pairs):
                inserted_this_pair += 1
        total_inserted += inserted_this_pair

        if pair_bridges:
            print(f"    {vibe_a} <-> {vibe_b}: "
                  f"{len(pair_bridges)} passed gate, kept {inserted_this_pair}")

    db.commit()
    print(f"    Total: {total_candidates} candidates, {total_passed_gate} passed gate, "
          f"{total_inserted} inserted")
    return total_inserted


# ---------------------------------------------------------------------------
# Pass 3: Shared Purpose (function-first)
# ---------------------------------------------------------------------------

def run_function_pass(db, product_map, embedding_cache, existing_pairs,
                      top_per_function=15, min_gate=0.25):
    """Find bridges between items sharing a social function across context boundaries.
    No vector search — candidates come from shared social_function values."""
    print("\n  Pass 3: Shared Purpose (function grouping)")

    products = list(product_map.values())
    func_index = build_function_index(products)

    total_inserted = 0

    for func_name, prod_ids in sorted(func_index.items(), key=lambda x: -len(x[1])):
        if len(prod_ids) < 2:
            continue

        func_bridges = []
        id_list = sorted(prod_ids)

        for i, a_id in enumerate(id_list):
            for b_id in id_list[i+1:]:
                lo, hi = a_id, b_id  # already sorted
                if (lo, hi) in existing_pairs:
                    continue

                a = product_map[a_id]
                b = product_map[b_id]

                # Must cross at least one context boundary
                diff_culture = (a.culture and b.culture
                               and (a.culture or '').strip().lower() != (b.culture or '').strip().lower())
                a_era_mid = _ERA_MIDPOINTS.get((a.era or '').strip().lower())
                b_era_mid = _ERA_MIDPOINTS.get((b.era or '').strip().lower())
                diff_era = (a_era_mid is not None and b_era_mid is not None
                           and abs(a_era_mid - b_era_mid) >= TRANSMISSION_DISTANCE)
                diff_cat = (a.fp_category and b.fp_category
                           and _get_category_group(a.fp_category) != _get_category_group(b.fp_category))

                if not (diff_culture or diff_era or diff_cat):
                    continue

                structural_score, shared = compute_structural_score(a, b)

                text_a, img_a = _get_embeddings(db, a_id, embedding_cache)
                text_b, img_b = _get_embeddings(db, b_id, embedding_cache)
                text_sim = _cosine_sim(text_a, text_b) or 0.0
                image_sim = _cosine_sim(img_a, img_b)

                # Gate: simple average
                components = [text_sim, structural_score]
                if image_sim is not None:
                    components.append(image_sim)
                gate = sum(components) / len(components)
                if gate < min_gate:
                    continue

                shared['discovery'] = 'function_match'
                shared['shared_function'] = func_name
                boundaries = []
                if diff_culture: boundaries.append('culture')
                if diff_era: boundaries.append('era')
                if diff_cat: boundaries.append('category')
                shared['boundaries_crossed'] = boundaries

                func_bridges.append({
                    'source_id': lo,
                    'target_id': hi,
                    'text_similarity': round(text_sim, 4),
                    'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                    'structural_score': round(structural_score, 4),
                    'shared_attributes': json.dumps(shared),
                    'bridge_type': 'function',
                    'created_at': datetime.now(tz=timezone.utc),
                })

        # Sort by average score, keep top N
        func_bridges.sort(
            key=lambda b: (b['text_similarity'] + (b['image_similarity'] or 0) + b['structural_score'])
                          / (3 if b['image_similarity'] is not None else 2),
            reverse=True
        )
        inserted_this_func = 0
        for b in func_bridges[:top_per_function]:
            if _insert_bridge(db, b, existing_pairs):
                inserted_this_func += 1
        total_inserted += inserted_this_func

        if func_bridges:
            print(f"    {func_name}: {len(func_bridges)} candidates, kept {inserted_this_func}")

    db.commit()
    print(f"    Total inserted: {total_inserted}")
    return total_inserted


# ---------------------------------------------------------------------------
# Pass 4: Parallel Form (structure-first)
# ---------------------------------------------------------------------------

def run_structural_pass(db, product_map, embedding_cache, existing_pairs,
                        min_structural=0.40, top_per_group=10,
                        discovery_bonus=0.10, bonus_threshold=0.4):
    """Find structural doppelgangers — same shape, different context.
    No vector search — candidates come from shared (category, silhouette) groups."""
    print("\n  Pass 4: Parallel Form (structural grouping)")

    products = list(product_map.values())
    groups = build_structural_groups(products)
    print(f"    {len(groups)} structural groups (category+silhouette, >=3 products)")

    total_inserted = 0

    for (cat, sil), prod_ids in sorted(groups.items(), key=lambda x: -len(x[1])):
        group_bridges = []
        id_list = sorted(prod_ids)

        for i, a_id in enumerate(id_list):
            for b_id in id_list[i+1:]:
                lo, hi = a_id, b_id
                if (lo, hi) in existing_pairs:
                    continue

                a = product_map[a_id]
                b = product_map[b_id]

                # Must cross at least one context boundary
                diff_era = (a.era and b.era
                           and (a.era or '').strip().lower() != (b.era or '').strip().lower())
                diff_culture = (a.culture and b.culture
                               and (a.culture or '').strip().lower() != (b.culture or '').strip().lower())
                diff_platform = a.platform != b.platform

                if not (diff_era or diff_culture or diff_platform):
                    continue

                structural_score, shared = compute_structural_score(a, b)
                if structural_score < min_structural:
                    continue

                text_a, img_a = _get_embeddings(db, a_id, embedding_cache)
                text_b, img_b = _get_embeddings(db, b_id, embedding_cache)
                text_sim = _cosine_sim(text_a, text_b) or 0.0
                image_sim = _cosine_sim(img_a, img_b)

                # Discovery bonus for independent invention (low text sim = different description)
                bonus = discovery_bonus if text_sim < bonus_threshold else 0.0
                sort_score = structural_score + bonus

                shared['discovery'] = 'structural_parallel'
                if bonus > 0:
                    shared['independent_invention'] = True

                group_bridges.append({
                    'source_id': lo,
                    'target_id': hi,
                    'text_similarity': round(text_sim, 4),
                    'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                    'structural_score': round(structural_score, 4),
                    'shared_attributes': json.dumps(shared),
                    'bridge_type': 'structural',
                    'created_at': datetime.now(tz=timezone.utc),
                    '_sort_score': sort_score,
                })

        group_bridges.sort(key=lambda b: b['_sort_score'], reverse=True)
        inserted_this_group = 0
        for b in group_bridges[:top_per_group]:
            del b['_sort_score']
            if _insert_bridge(db, b, existing_pairs):
                inserted_this_group += 1
        total_inserted += inserted_this_group

        if group_bridges:
            print(f"    {cat}/{sil}: {len(group_bridges)} candidates, kept {inserted_this_group}")

    db.commit()
    print(f"    Total inserted: {total_inserted}")
    return total_inserted


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def compute_bridges(rebuild=False, limit=None,
                    top_k=20, top_n=5,
                    min_structural_open=0.30,
                    min_bridge=0.40):
    """
    Compute style bridges with four passes:
      1. Similarity   — vector proximity (affinity/resonance)
      2. Opposition   — opposing core_vibes cross-join (contrast)
      3. Shared Purpose — shared social_function across context (comparison)
      4. Parallel Form — shared (category, silhouette) across context (independent invention)
    """
    db = SessionLocal()

    print("\n" + "=" * 70)
    print("COMPUTING STYLE BRIDGES")
    print("  4 passes: similarity | opposition | function | structural")
    print("=" * 70)

    # --- Load products -------------------------------------------------
    products = db.query(Product).filter(Product.enriched_at != None).all()
    product_map = {p.id: p for p in products}

    # --- Check embeddings ----------------------------------------------
    text_ids, image_ids = get_embedded_ids(db)

    eligible = [p for p in products if p.id in text_ids]
    if limit:
        eligible = eligible[:limit]

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
        print("\n  No eligible products. Generate embeddings first.")
        db.close()
        return

    if rebuild:
        deleted = db.query(StyleBridge).delete()
        db.commit()
        print(f"\n  Cleared {deleted} existing bridges.")

    # Pass 1 only — passes 2-4 run after the per-product loop
    passes = [
        ('similarity', top_n, build_open_filter, None, min_structural_open),
    ]

    # Skip products that already have bridges (for resuming interrupted runs)
    already_bridged = set()
    if not rebuild:
        rows = db.execute(
            text("SELECT DISTINCT source_id FROM style_bridges")
        ).fetchall()
        already_bridged = {r[0] for r in rows}
        if already_bridged:
            print(f"\n  Resuming: {len(already_bridged)} products already bridged, skipping them.")

    print(f"\n  Parameters: top_k={top_k}  min_structural={min_structural_open}  "
          f"min_bridge={min_bridge}")
    print(f"  Pass 1 (similarity): top_n={top_n} per product")
    print("\n" + "-" * 70)
    print("Starting...\n")

    total_stored = 0
    total_by_pass = {name: 0 for name, *_ in passes}
    skipped_structural = 0
    skipped_bridge = 0
    skipped_resume = 0
    existing_pairs = set()  # tracks all inserted pairs for dedup across all passes
    embedding_cache = {}     # shared across all passes to avoid redundant DB fetches
    start_time = time.time()

    for i, product in enumerate(eligible):
        # Skip already-processed products on resume
        if product.id in already_bridged:
            skipped_resume += 1
            continue
        # --- Retrieve source vectors (once per product, cached for passes 2-4) ---
        text_vector, image_vector = _get_embeddings(db, product.id, embedding_cache)
        if text_vector is None:
            continue

        product_bridges = 0

        # --- Run each pass ---------------------------------------------
        for pass_name, pass_top_n, filter_fn, type_override, min_structural in passes:
            filter_result = filter_fn(product)
            if filter_result[0] is None:
                continue
            exclude_sql, exclude_params = filter_result

            candidates = search_candidates_pgvector(
                db, product.id, text_vector, image_vector,
                exclude_sql, exclude_params, top_k,
            )


            bridges, stats = score_candidates(
                product, candidates, product_map,
                min_structural, min_bridge, type_override,
                pass_name=pass_name,
            )

            skipped_structural += stats['skipped_structural']
            skipped_bridge += stats['skipped_bridge']

            # Keep top N for this pass
            bridges.sort(key=lambda b: (b['text_similarity'] + (b['image_similarity'] or 0) + b['structural_score']) / (3 if b['image_similarity'] is not None else 2), reverse=True)
            bridges = bridges[:pass_top_n]

            # Insert via _insert_bridge (dedup + accurate counting)
            for b in bridges:
                if b['source_id'] == b['target_id']:
                    continue  # never bridge an item to itself
                if _insert_bridge(db, b, existing_pairs):
                    product_bridges += 1
                    total_by_pass[pass_name] += 1

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
    pass1_elapsed = time.time() - start_time
    print(f"\n  Pass 1 complete: {total_stored} bridges in {pass1_elapsed:.1f}s")

    # --- Passes 2-4: non-vector candidate selection --------------------
    print("\n" + "-" * 70)
    print("Running passes 2-4 (opposition, function, structural)...\n")
    print(f"  {len(existing_pairs)} existing bridge pairs tracked for dedup")
    print(f"  {len(embedding_cache)} embeddings cached from Pass 1")

    # Fresh session between each pass — pooler drops idle connections
    def fresh_db(old_db):
        try:
            old_db.close()
        except Exception:
            pass
        return SessionLocal()

    db = fresh_db(db)
    opposition_count = run_opposition_pass(db, product_map, embedding_cache, existing_pairs)
    total_by_pass['opposition'] = opposition_count

    db = fresh_db(db)
    function_count = run_function_pass(db, product_map, embedding_cache, existing_pairs)
    total_by_pass['function'] = function_count

    db = fresh_db(db)
    structural_count = run_structural_pass(db, product_map, embedding_cache, existing_pairs)
    total_by_pass['structural'] = structural_count

    total_stored += opposition_count + function_count + structural_count
    elapsed = time.time() - start_time

    # --- Summary -------------------------------------------------------
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"\n  Products processed:       {len(eligible) - skipped_resume}")
    print(f"  Skipped (already bridged):{skipped_resume}")
    print(f"  Bridges stored:           {total_stored}")
    print(f"  Skipped (low structural): {skipped_structural}")
    print(f"  Skipped (low gate score): {skipped_bridge}")
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

    # Top bridges (by text similarity as a sensible default)
    top = (
        db.query(StyleBridge)
        .order_by(StyleBridge.text_similarity.desc())
        .limit(5)
        .all()
    )
    if top:
        print(f"\n  Top 5 bridges (by text similarity):")
        for b in top:
            src = product_map.get(b.source_id)
            tgt = product_map.get(b.target_id)
            s_name = src.title[:30] if src else f"#{b.source_id}"
            t_name = tgt.title[:30] if tgt else f"#{b.target_id}"
            s_era = src.era or '?' if src else '?'
            t_era = tgt.era or '?' if tgt else '?'
            print(f"    text={b.text_similarity:.3f}  img={b.image_similarity or 0:.3f}  struct={b.structural_score:.3f}  [{b.bridge_type}]")
            print(f"      {s_name} ({s_era})")
            print(f"      -> {t_name} ({t_era})")
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
