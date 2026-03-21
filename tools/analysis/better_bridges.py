"""
compute_bridges.py — Entity-based bridge discovery

Three passes:
  Pass 1: Shared Entities — products sharing rare, meaningful entities
  Pass 2: Lineage — directed bridges from influence_references
  Pass 3: Visual Echo — high image similarity not already connected

Scoring: IDF-weighted entity overlap + context bonus + embedding bonus
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import argparse
import math
import re
import json
import time
import logging
from collections import defaultdict
import numpy as np
from sqlalchemy import text

from storage.database import SessionLocal, Product, StyleBridge

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Entity type multipliers — how important each connection type is
ENTITY_MULTIPLIERS = {
    'designer':                3.0,   # most intentional connection
    'influence_references':    2.5,   # explicit citation
    'named_movements':         2.0,   # conceptual connection
    'garment_system':          1.5,   # shared body philosophy
    'construction_technique':  1.0,   # shared craft (baseline)
    'social_function':         1.0,   # shared purpose
    'motif_family':            0.75,  # decorative, least structural
}

# Entity values too common to be meaningful as sole connection reason
# These still contribute to entity_score but don't satisfy the has_rare_entity gate
ENTITY_BLOCKLIST = {
    'social_function': {'everyday-practical', 'status-signaling'},
    'construction_technique': {'hand-sewing', 'machine-sewing', 'tailoring'},
    'motif_family': {'none', 'geometric', 'floral'},
}

# Fields that store JSON arrays vs plain strings
ARRAY_FIELDS = [
    'named_movements', 'construction_technique', 'social_function',
    'motif_family', 'influence_references', 'garment_system',
]
STRING_FIELDS = ['designer']

# Context scoring
CONTEXT_WEIGHTS = {
    'year_gap_per_decade': 0.05,      # +0.05 per decade apart, caps at 0.5
    'cross_culture':       0.4,
    'cross_category':      0.05,       # not very interesting on its own
    'cross_category_culture': 0.35,
}

# Gates and caps
MIN_ENTITY_SCORE = 5.0          # minimum IDF-weighted score to create a bridge
MIN_ENTITY_IDF = 2.0            # at least one shared entity must have IDF >= this (roughly <=500 products)
MAX_BRIDGES_PER_PRODUCT = 15    # across all passes
MAX_PAIRS_PER_ENTITY = 200      # cap per shared entity value to prevent common-term explosion
TOO_SIMILAR_TEXT = 0.90         # same-era text similarity ceiling
TOO_SIMILAR_IMAGE = 0.93        # image similarity ceiling
TOO_SIMILAR_COMBINED = 0.87     # average of text + image ceiling
VISUAL_ECHO_MIN_IMAGE_SIM = 0.80  # minimum image similarity for Pass 3
LINEAGE_MIN_TEXT_SIM = 0.40     # minimum similarity for influence matching
BOUNDARY_YEAR_GAP = 30          # minimum year gap when same culture
SAME_ERA_MIN_ENTITY_SCORE = 8.0 # stricter gate when both products share an era
SAME_ERA_MAX_BRIDGES = 300      # max bridges between products of the same era

# ---------------------------------------------------------------------------
# Product Index & IDF
# ---------------------------------------------------------------------------

ERA_MIDPOINTS = {
    # Pre-modern
    'Ancient Roman': 100, 'Gothic / High Medieval': 1250, 'Late Medieval': 1400,
    'Northern Renaissance': 1480, 'Italian Renaissance': 1490, 'Renaissance': 1500,
    'Elizabethan': 1580, 'Jacobean': 1615, 'Restoration': 1670,
    'Baroque': 1660, 'Rococo': 1740,
    # 18th-19th century transitions
    'Neoclassical Transition': 1775, 'Revolutionary / Directoire': 1795,
    'Empire / Regency': 1810, 'Romantic': 1835,
    'Victorian Early / Crinoline': 1855, 'Victorian Late / Bustle': 1880,
    'Belle Epoque': 1890, 'Fin de Siecle / Gibson Girl': 1895,
    # Early 20th century
    'Edwardian': 1905, 'World War I Transition': 1916,
    'Roaring Twenties / Art Deco': 1925, 'Great Depression': 1935,
    'Wartime / Utility Fashion': 1943, 'New Look / Post-War': 1950,
    # Mid-20th century
    'Atomic Age': 1955, 'Space Age': 1963,
    'Hippie / Counterculture': 1968, 'Glam Rock': 1973,
    'Punk': 1977, 'Disco': 1977,
    # 1980s-1990s
    'New Romanticism': 1982, 'Power Dressing': 1985,
    'Hip-Hop': 1990, 'Grunge': 1993, 'Rave / Club Kid': 1994,
    'Supermodel Era': 1996, 'Minimalism': 1997,
    # 2000s-2020s
    'Y2K': 2002, 'Indie Sleaze': 2008, 'Normcore': 2010,
    'Dark Academia': 2014, 'Athleisure': 2015, 'Gorpcore': 2018,
    'Cottagecore': 2020, 'Dopamine Dressing': 2021,
    'Quiet Luxury': 2022, 'Preppy / Ivy League': 2022,
}


def _parse_json_field(value):
    """Parse a JSON array field into a set. Returns empty set on failure."""
    if value is None:
        return set()
    if isinstance(value, list):
        return set(v for v in value if v and v != 'none')
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return set(v for v in parsed if v and v != 'none')
        except (json.JSONDecodeError, TypeError):
            pass
    return set()


def _get_year(product):
    """Best estimate of a product's year from decade or era.
    Returns (year, precision) where precision is 'decade' or 'era'.
    Decade is ±5 years, era midpoint is ±20-30 years."""
    if product.decade:
        try:
            return int(product.decade.rstrip('s')), 'decade'
        except (ValueError, AttributeError):
            pass
    if product.era and product.era in ERA_MIDPOINTS:
        return ERA_MIDPOINTS[product.era], 'era'
    return None, None


def _get_category_group(product):
    """Broad category for crossing detection."""
    fp = product.fp_category
    if not fp:
        return None
    GROUPS = {
        'dress': 'dresses', 'gown': 'dresses',
        'shirt': 'tops', 'blouse': 'tops', 'top': 'tops', 't-shirt': 'tops',
        'jacket': 'outerwear', 'coat': 'outerwear', 'cape': 'outerwear',
        'pants': 'bottoms', 'trousers': 'bottoms', 'skirt': 'bottoms', 'shorts': 'bottoms',
        'shoe': 'footwear', 'boot': 'footwear', 'sandal': 'footwear', 'slipper': 'footwear',
        'hat': 'headwear', 'bonnet': 'headwear', 'cap': 'headwear',
        'bag': 'accessories', 'glove': 'accessories', 'scarf': 'accessories',
    }
    fp_lower = fp.lower()
    for key, group in GROUPS.items():
        if key in fp_lower:
            return group
    return fp_lower


def build_product_index(db):
    """Load all products, parse entities, build inverted index and IDF.
    
    Returns:
        product_map:     {id: {...parsed product data...}}
        inverted_index:  {(entity_type, value): set(product_ids)}
        idf:             {(entity_type, value): float}
    """
    log.info('Loading products...')
    products = db.query(Product).filter(Product.enriched_at.isnot(None)).all()
    total = len(products)
    log.info(f'  {total} enriched products loaded')

    product_map = {}
    inverted_index = defaultdict(set)

    for p in products:
        entities = {}
        
        # Parse array fields
        for field in ARRAY_FIELDS:
            values = _parse_json_field(getattr(p, field, None))
            if values:
                entities[field] = values
                for v in values:
                    inverted_index[(field, v)].add(p.id)
        
        # Parse string fields
        for field in STRING_FIELDS:
            value = getattr(p, field, None)
            if value and value.strip():
                entities[field] = {value.strip()}
                inverted_index[(field, value.strip())].add(p.id)
        
        year, year_precision = _get_year(p)
        product_map[p.id] = {
            'id': p.id,
            'product': p,
            'entities': entities,
            'year': year,
            'year_precision': year_precision,
            'era': p.era,
            'decade': p.decade,
            'culture': p.culture,
            'category': _get_category_group(p),
            'title': p.title,
            'display_title': p.display_title or p.title,
        }

    # Compute IDF
    log.info('  Computing IDF...')
    idf = {}
    for key, pid_set in inverted_index.items():
        count = len(pid_set)
        idf[key] = math.log(total / count)

    log.info(f'  {len(inverted_index)} distinct entity values indexed')
    
    # Log entity stats
    by_type = defaultdict(int)
    for (etype, _) in inverted_index:
        by_type[etype] += 1
    for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        log.info(f'    {etype}: {count} distinct values')
    
    return product_map, inverted_index, idf

#
# ---------------------------------------------------------------------------
# Progress Logging
# ---------------------------------------------------------------------------

class ProgressTracker:
    """Simple progress tracker with rate and ETA."""
    
    def __init__(self, total, label=''):
        self.total = total
        self.label = label
        self.count = 0
        self.start = time.time()
    
    def tick(self, n=1):
        self.count += n
    
    def log_every(self, interval=500):
        if self.count % interval == 0 or self.count == self.total:
            elapsed = time.time() - self.start
            rate = self.count / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.count) / rate if rate > 0 else 0
            log.info(
                f'  [{self.count:>6}/{self.total}]  '
                f'{rate:.1f}/s  ETA {remaining:.0f}s'
                f'  {self.label}'
            )


# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------

def score_entity_overlap(prod_a, prod_b, idf):
    """Score the entity overlap between two products.

    For each entity type, find the intersection of values.
    Weight each shared value by its IDF (rarity) × type multiplier.

    Returns:
        entity_score: float
        shared_entities: dict of {entity_type: [values]} — only types with overlap
        has_rare_entity: bool — True if at least one shared entity has IDF >= MIN_ENTITY_IDF
    """
    shared = {}
    score = 0.0
    max_idf = 0.0

    for entity_type, multiplier in ENTITY_MULTIPLIERS.items():
        set_a = prod_a['entities'].get(entity_type, set())
        set_b = prod_b['entities'].get(entity_type, set())
        overlap = set_a & set_b

        if overlap:
            # Only store non-blocklisted values in shared_entities
            blocklist = ENTITY_BLOCKLIST.get(entity_type, set())
            display_values = sorted(v for v in overlap if v not in blocklist)
            if display_values:
                shared[entity_type] = display_values
            for value in overlap:
                entity_idf = idf.get((entity_type, value), 0)
                # For construction_technique and garment_system, only apply
                # multiplier if the value is sufficiently rare (IDF >= 2.0)
                if entity_type in ('construction_technique', 'garment_system') and entity_idf < MIN_ENTITY_IDF:
                    effective_multiplier = 0.25  # token contribution, not zero
                else:
                    effective_multiplier = multiplier
                score += entity_idf * effective_multiplier
                # Only count as "rare" if not blocklisted
                if value not in ENTITY_BLOCKLIST.get(entity_type, set()):
                    if entity_idf > max_idf:
                        max_idf = entity_idf

    has_rare_entity = max_idf >= MIN_ENTITY_IDF
    return score, shared, has_rare_entity

def compute_context_score(prod_a, prod_b):
    """Score based on how much context the bridge crosses.
    
    Rewards year gap (more distance = more interesting),
    culture crossing, and category crossing.
    
    Returns:
        context_score: float
        year_gap: int or None
        crossing_type: str
    """
    score = 0.0

    # Year gap — discount if derived from era midpoints (less precise)
    year_a = prod_a['year']
    year_b = prod_b['year']
    year_gap = abs(year_a - year_b) if (year_a and year_b) else None

    if year_gap is not None:
        decades = min(year_gap / 10, 10)  # cap at 100 years
        # Discount if either year is from an era midpoint rather than a decade
        prec_a = prod_a.get('year_precision', 'era')
        prec_b = prod_b.get('year_precision', 'era')
        if prec_a == 'decade' and prec_b == 'decade':
            precision_factor = 1.0   # both precise — full credit
        elif prec_a == 'decade' or prec_b == 'decade':
            precision_factor = 0.7   # one precise — moderate credit
        else:
            precision_factor = 0.4   # both midpoints — low credit
        score += decades * CONTEXT_WEIGHTS['year_gap_per_decade'] * precision_factor

    # Crossing type
    diff_culture = (prod_a['culture'] or '') != (prod_b['culture'] or '')
    diff_category = (prod_a['category'] or '') != (prod_b['category'] or '')

    if diff_culture and diff_category:
        crossing_type = 'cross_category_culture'
        score += CONTEXT_WEIGHTS['cross_category_culture']
    elif diff_culture:
        crossing_type = 'cross_culture'
        score += CONTEXT_WEIGHTS['cross_culture']
    elif diff_category:
        crossing_type = 'cross_category'
        score += CONTEXT_WEIGHTS['cross_category']
    else:
        crossing_type = 'same_context'

    return score, year_gap, crossing_type

def _too_similar(prod_a, prod_b, text_sim=None, image_sim=None):
    """Reject pairs that are basically the same item.
    
    Returns True if the pair should be skipped.
    """
    same_era = (prod_a['era'] == prod_b['era']) and prod_a['era'] is not None

    # Same era + very high text similarity
    if same_era and text_sim is not None and text_sim >= TOO_SIMILAR_TEXT:
        return True

    # Very high image similarity + moderate text similarity
    if (image_sim is not None and text_sim is not None
            and image_sim >= TOO_SIMILAR_IMAGE and text_sim >= 0.65):
        return True

    # Combined average too high
    if text_sim is not None and image_sim is not None:
        avg = (text_sim + image_sim) / 2
        if avg >= TOO_SIMILAR_COMBINED:
            return True

    return False

def _crosses_boundary(prod_a, prod_b):
    """Check if two products are different enough to bridge.
    
    Requires 20+ year gap OR different culture.
    Lineage bridges skip this check (they're inherently cross-time).
    """
    year_a = prod_a['year']
    year_b = prod_b['year']

    if year_a and year_b and abs(year_a - year_b) >= BOUNDARY_YEAR_GAP:
        return True

    culture_a = prod_a['culture'] or ''
    culture_b = prod_b['culture'] or ''
    if culture_a and culture_b and culture_a != culture_b:
        return True

    return False

def _parse_influence_era(influence_str):
    """Extract decade or era hints from an influence reference string.

    Returns (decade_str, era_name) — at most one will be set.
    """
    # Match decades like "1890s", "1920s"
    decade_match = re.search(r'(\d{4})s', influence_str)
    if decade_match:
        return decade_match.group(0), None

    # Match "18th century", "19th century"
    century_match = re.search(r'(\d{1,2})(?:th|st|nd|rd)\s*century', influence_str.lower())
    if century_match:
        c = int(century_match.group(1))
        # Map century to approximate era
        century_eras = {
            14: 'Medieval', 15: 'Renaissance', 16: 'Elizabethan',
            17: 'Baroque', 18: 'Rococo', 19: 'Victorian Early / Crinoline',
            20: 'Roaring Twenties / Art Deco',
        }
        return None, century_eras.get(c)

    # Match against canonical ERA_MIDPOINTS keys
    # Build keyword → era mapping from canonical eras
    # Split era names into searchable keywords
    influence_lower = influence_str.lower()

    # First try exact substring match against canonical era names
    for era_name in ERA_MIDPOINTS:
        if era_name.lower() in influence_lower:
            return None, era_name

    # Then try common shorthand keywords that map to canonical eras
    era_shorthands = {
        'victorian': 'Victorian',           # partial match for Early/Late
        'regency': 'Empire / Regency',
        'empire': 'Empire / Regency',
        'art deco': 'Roaring Twenties / Art Deco',
        'jazz age': 'Roaring Twenties / Art Deco',
        'flapper': 'Roaring Twenties / Art Deco',
        'new look': 'New Look / Post-War',
        'post-war': 'New Look / Post-War',
        'neoclassical': 'Neoclassical Transition',
        'directoire': 'Revolutionary / Directoire',
        'gibson girl': 'Fin de Siecle / Gibson Girl',
        'fin de siecle': 'Fin de Siecle / Gibson Girl',
        'belle epoque': 'Fin de Siecle / Gibson Girl',
        'crinoline': 'Victorian Early / Crinoline',
        'bustle': 'Victorian Late / Bustle',
        'counterculture': 'Hippie / Counterculture',
        'hippie': 'Hippie / Counterculture',
        'mod': 'Space Age',          # Mod and Space Age overlap (~1963)
        'punk': 'Punk',
        'power dressing': 'Power Dressing',
        'grunge': 'Grunge',
        'hip-hop': 'Hip-Hop',
        'hip hop': 'Hip-Hop',
        'rave': 'Rave / Club Kid',
        'club kid': 'Rave / Club Kid',
        'normcore': 'Normcore',
        'athleisure': 'Athleisure',
        'cottagecore': 'Cottagecore',
        'gorpcore': 'Gorpcore',
        'dark academia': 'Dark Academia',
        'indie sleaze': 'Indie Sleaze',
        'minimalism': 'Minimalism',
        'minimalist': 'Minimalism',
    }
    for keyword, era in era_shorthands.items():
        if keyword in influence_lower:
            return None, era

    return None, None


def _cosine_sim(emb_a, emb_b):
    """Cosine similarity between two embedding vectors. Returns None if either is missing."""
    if emb_a is None or emb_b is None:
        return None
    dot = np.dot(emb_a, emb_b)
    norm = np.linalg.norm(emb_a) * np.linalg.norm(emb_b)
    if norm == 0:
        return None
    return float(dot / norm)


def compute_bridge_score(entity_score, context_score, text_sim=None, image_sim=None):
    """Final bridge score combining all signals.
    
    entity_score:  IDF-weighted entity overlap (the "why")
    context_score: year gap + crossing bonuses (the "distance")
    text_sim:      text embedding similarity (confirmation signal)
    image_sim:     image embedding similarity (confirmation signal)
    
    Returns normalized score 0-1.
    """
    # Embedding bonus — small confirmation boost, not a primary signal
    embedding_bonus = 0.0
    if text_sim is not None:
        embedding_bonus += text_sim * 0.1   # max +0.1
    if image_sim is not None:
        embedding_bonus += image_sim * 0.1  # max +0.1

    # Surprise bonus — high entity overlap + low visual similarity
    # "They share real DNA but you'd never guess from looking at them"
    surprise_bonus = 0.0
    if entity_score >= 8.0 and image_sim is not None and image_sim < 0.4:
        surprise_bonus = (1.0 - image_sim) * 0.3  # max +0.3 when image_sim=0
    elif entity_score >= 8.0 and text_sim is not None and text_sim < 0.5 and image_sim is None:
        surprise_bonus = (1.0 - text_sim) * 0.15  # weaker fallback when no image

    raw = entity_score + context_score + embedding_bonus + surprise_bonus

    # Normalize to 0-1 range using sigmoid-like scaling
    # A raw score of 10 → ~0.7, raw score of 20 → ~0.85, raw score of 40 → ~0.95
    normalized = 1 - (1 / (1 + raw / 10))

    return round(normalized, 4)

# ---------------------------------------------------------------------------
# Pass 1: Shared Entities
# ---------------------------------------------------------------------------

def pass_1_shared_entities(product_map, inverted_index, idf, existing_pairs, participation):
    """Find bridges between products that share rare, meaningful entities.
    
    Uses the inverted index to avoid N² comparison — for each entity value,
    cross-join the products that share it, score the overlap, and keep
    bridges that pass the gates.
    
    Returns list of bridge dicts ready for DB insertion.
    """
    log.info('\n' + '=' * 70)
    log.info('  Pass 1: Shared Entities')
    log.info('=' * 70)

    # Collect all candidate pairs from the inverted index
    # For each entity value, every pair of products sharing it is a candidate
    log.info('  Building candidate pairs from inverted index...')
    candidate_pairs = set()
    skipped_common = 0

    for (entity_type, value), pid_set in inverted_index.items():
        # Skip entity values with too many products (noise)
        if len(pid_set) > MAX_PAIRS_PER_ENTITY:
            skipped_common += 1
            continue
        # Skip single-product entities (no pairs possible)
        if len(pid_set) < 2:
            continue
        # Generate all pairs (canonical order: smaller id first)
        pids = sorted(pid_set)
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                candidate_pairs.add((pids[i], pids[j]))

    log.info(f'  {len(candidate_pairs)} candidate pairs from {len(inverted_index)} entity values')
    log.info(f'  {skipped_common} entity values skipped (>{MAX_PAIRS_PER_ENTITY} products)')

    if len(candidate_pairs) > 1_000_000:
        log.warning(f'  WARNING: {len(candidate_pairs)} pairs is very large. '
                     f'Consider lowering MAX_PAIRS_PER_ENTITY (currently {MAX_PAIRS_PER_ENTITY})')

    # Score each candidate pair
    bridges = []
    scored = 0
    below_gate = 0
    too_similar_count = 0
    no_boundary = 0
    same_era_capped = 0
    same_era_counts = defaultdict(int)  # era → count of same-era bridges

    tracker = ProgressTracker(len(candidate_pairs), label='scoring')

    for id_a, id_b in candidate_pairs:
        tracker.tick()
        tracker.log_every(5000)

        pair_key = (id_a, id_b)
        if pair_key in existing_pairs:
            continue

        prod_a = product_map[id_a]
        prod_b = product_map[id_b]

        # Gate: must cross a boundary
        if not _crosses_boundary(prod_a, prod_b):
            no_boundary += 1
            continue

        # Detect same-era pairs
        same_era = (prod_a['era'] and prod_b['era'] and prod_a['era'] == prod_b['era'])

        # Gate: per-era cap for same-era bridges
        if same_era and same_era_counts[prod_a['era']] >= SAME_ERA_MAX_BRIDGES:
            same_era_capped += 1
            continue

        # Score entity overlap
        entity_score, shared_entities, has_rare = score_entity_overlap(prod_a, prod_b, idf)

        # Stricter gate for same-era bridges — need more specific shared entities
        min_score = SAME_ERA_MIN_ENTITY_SCORE if same_era else MIN_ENTITY_SCORE
        if entity_score < min_score or not has_rare:
            below_gate += 1
            continue

        # Gate: not too similar (need embeddings for this)
        # We'll compute text/image sim lazily only for pairs that pass entity gate
        text_sim = _cosine_sim(prod_a.get('text_emb'), prod_b.get('text_emb'))
        image_sim = _cosine_sim(prod_a.get('image_emb'), prod_b.get('image_emb'))

        if _too_similar(prod_a, prod_b, text_sim, image_sim):
            too_similar_count += 1
            continue

        # Gate: participation cap
        if (participation.get(id_a, 0) >= MAX_BRIDGES_PER_PRODUCT or
                participation.get(id_b, 0) >= MAX_BRIDGES_PER_PRODUCT):
            continue

        # Score context
        context_score, year_gap, crossing_type = compute_context_score(prod_a, prod_b)

        # Final bridge score
        bridge_score = compute_bridge_score(entity_score, context_score, text_sim, image_sim)

        bridges.append({
            'source_id': id_a,
            'target_id': id_b,
            'connection_mode': 'shared_entity',
            'directed': False,
            'shared_entities': json.dumps(shared_entities),
            'entity_score': round(entity_score, 4),
            'bridge_score': bridge_score,
            'text_similarity': round(text_sim, 4) if text_sim is not None else None,
            'image_similarity': round(image_sim, 4) if image_sim is not None else None,
            'year_gap': year_gap,
            'crossing_type': crossing_type,
        })

        existing_pairs.add(pair_key)
        participation[id_a] = participation.get(id_a, 0) + 1
        participation[id_b] = participation.get(id_b, 0) + 1
        if same_era:
            same_era_counts[prod_a['era']] += 1
        scored += 1

    log.info(f'\n  Pass 1 complete:')
    log.info(f'    {scored} bridges created')
    log.info(f'    {below_gate} below entity score gate')
    log.info(f'    {no_boundary} rejected (no boundary crossing)')
    log.info(f'    {too_similar_count} rejected (too similar)')
    log.info(f'    {same_era_capped} rejected (same-era cap)')
    if same_era_counts:
        log.info(f'    Same-era bridges by era:')
        for era, cnt in sorted(same_era_counts.items(), key=lambda x: -x[1])[:10]:
            log.info(f'      {era:40s} {cnt:>5}')

    return bridges

# ---------------------------------------------------------------------------
# Pass 2: Lineage (directed)
# ---------------------------------------------------------------------------

def pass_2_lineage(product_map, idf, existing_pairs, participation):
    """Find directed bridges from influence_references to matching products.
    
    For each product with influence_references, search the corpus for products
    that ARE what's being referenced. Uses text similarity between the 
    influence string and product enriched_text to find matches.
    
    Bridges are directed: source = older product (the original),
    target = newer product (the one citing the influence).
    Always flows forward in time.
    
    Returns list of bridge dicts ready for DB insertion.
    """
    log.info('\n' + '=' * 70)
    log.info('  Pass 2: Lineage (directed)')
    log.info('=' * 70)

    # Collect products that have influence_references
    referencers = []
    for pid, prod in product_map.items():
        influences = prod['entities'].get('influence_references', set())
        if influences:
            referencers.append((pid, influences))

    log.info(f'  {len(referencers)} products with influence_references')

    # Build word-to-product inverted index for fast influence matching
    word_index = defaultdict(set)  # word → set of product ids
    product_search_text = {}       # pid → full search text
    
    for pid, prod in product_map.items():
        parts = [
            prod['display_title'],
            prod['era'] or '',
            prod['decade'] or '',      # Fix 3: add decade
            prod['culture'] or '',
            prod['category'] or '',
        ]
        for m in prod['entities'].get('named_movements', set()):
            parts.append(m)
        for t in prod['entities'].get('construction_technique', set()):
            parts.append(t)
        full_text = ' '.join(parts).lower()
        product_search_text[pid] = full_text
        for word in set(full_text.split()):
            if len(word) >= 3:  # skip tiny words
                word_index[word].add(pid)
    
    log.info(f'  Search index: {len(word_index)} words')


    bridges = []
    matched = 0
    no_match = 0
    matched_by_embedding = 0
    too_similar_count = 0

    total_influences = sum(len(infs) for _, infs in referencers)
    tracker = ProgressTracker(total_influences, label='influence refs')

    for referencer_id, influences in referencers:
        referencer = product_map[referencer_id]
        referencer_year = referencer['year']

        for influence_str in influences:
            tracker.tick()
            tracker.log_every(500)

            influence_lower = influence_str.lower()
            influence_words = set(influence_lower.split())

            # --- Fix 1: Parse era/decade from influence string ---
            decade_hint, era_hint = _parse_influence_era(influence_str)

            # --- Fix 2: Word index candidates with era pre-filter ---
            candidate_counts = defaultdict(int)
            for word in influence_words:
                if len(word) >= 3:
                    for cid in word_index.get(word, set()):
                        if cid != referencer_id:
                            candidate_counts[cid] += 1

            # Only consider candidates with ≥2 word matches
            word_candidates = [cid for cid, cnt in candidate_counts.items() if cnt >= 2]

            # Pre-filter by era/decade if we have a hint
            if decade_hint:
                era_filtered = [cid for cid in word_candidates
                                if product_map.get(cid, {}).get('decade') == decade_hint]
                if era_filtered:
                    word_candidates = era_filtered
            elif era_hint:
                era_filtered = [cid for cid in word_candidates
                                if product_map.get(cid, {}).get('era') and
                                era_hint.lower() in product_map[cid]['era'].lower()]
                if era_filtered:
                    word_candidates = era_filtered

            best_match = None
            best_score = 0

            for candidate_id in word_candidates:
                candidate = product_map[candidate_id]

                # Year direction check: candidate should be OLDER than referencer
                candidate_year = candidate['year']
                if referencer_year and candidate_year:
                    if candidate_year > referencer_year:
                        continue

                word_hits = candidate_counts[candidate_id]
                word_score = word_hits / len(influence_words) if influence_words else 0

                # Bonus for matching era mentioned in influence
                era_bonus = 0
                if candidate['era'] and candidate['era'].lower() in influence_lower:
                    era_bonus = 0.3
                elif decade_hint and candidate.get('decade') == decade_hint:
                    era_bonus = 0.25

                # Bonus for matching movement
                movement_bonus = 0
                for m in candidate['entities'].get('named_movements', set()):
                    if m.lower() in influence_lower:
                        movement_bonus = 0.3
                        break

                total_score = word_score + era_bonus + movement_bonus

                if total_score > best_score:
                    best_score = total_score
                    best_match = candidate_id

            # --- Embedding fallback for unmatched influences ---
            used_embedding_fallback = False
            if (best_match is None or best_score < 0.4) and referencer.get('text_emb') is not None:
                # Build candidate pool: prefer era-filtered, fall back to word candidates
                if decade_hint:
                    fallback_pool = [pid for pid, prod in product_map.items()
                                     if prod.get('decade') == decade_hint
                                     and pid != referencer_id
                                     and prod.get('text_emb') is not None]
                elif era_hint:
                    fallback_pool = [pid for pid, prod in product_map.items()
                                     if prod.get('era') and era_hint.lower() in prod['era'].lower()
                                     and pid != referencer_id
                                     and prod.get('text_emb') is not None]
                else:
                    # No era hint — use word candidates even with 1 match
                    fallback_pool = [cid for cid, cnt in candidate_counts.items()
                                     if cnt >= 1
                                     and product_map.get(cid, {}).get('text_emb') is not None]

                # Sort by word overlap count (best partial matches first)
                fallback_pool.sort(
                    key=lambda cid: candidate_counts.get(cid, 0), reverse=True
                )

                best_emb_sim = LINEAGE_MIN_TEXT_SIM
                best_emb_match = None

                for cid in fallback_pool[:300]:  # cap to avoid slow scan
                    cand = product_map.get(cid)
                    if cand is None:
                        continue
                    # Year direction
                    cand_year = cand['year']
                    if referencer_year and cand_year and cand_year > referencer_year:
                        continue
                    sim = _cosine_sim(referencer.get('text_emb'), cand.get('text_emb'))
                    if sim and sim > best_emb_sim:
                        best_emb_sim = sim
                        best_emb_match = cid

                if best_emb_match is not None:
                    best_match = best_emb_match
                    best_score = best_emb_sim
                    used_embedding_fallback = True

            # Gate: minimum match quality
            if best_match is None or best_score < 0.4:
                no_match += 1
                continue

            match = product_map[best_match]

            # Directed ordering: source = older (the original), target = newer (the referencer)
            source_id = best_match
            target_id = referencer_id

            # Canonical pair key for dedup (always smaller first)
            pair_key = (min(source_id, target_id), max(source_id, target_id))
            if pair_key in existing_pairs:
                continue

            # Gate: not too similar
            text_sim = _cosine_sim(match.get('text_emb'), referencer.get('text_emb'))
            image_sim = _cosine_sim(match.get('image_emb'), referencer.get('image_emb'))

            if _too_similar(match, referencer, text_sim, image_sim):
                too_similar_count += 1
                continue

            # Gate: participation cap
            if (participation.get(source_id, 0) >= MAX_BRIDGES_PER_PRODUCT or
                    participation.get(target_id, 0) >= MAX_BRIDGES_PER_PRODUCT):
                continue

            # Score — lineage reference itself counts as a high-value entity connection
            LINEAGE_BONUS = 5.0
            entity_score, shared_entities, _ = score_entity_overlap(match, referencer, idf)
            entity_score += LINEAGE_BONUS
            context_score, year_gap, crossing_type = compute_context_score(match, referencer)
            bridge_score = compute_bridge_score(entity_score, context_score, text_sim, image_sim)

            # Add the influence reference as the lineage reason
            lineage_data = shared_entities.copy()
            lineage_data['lineage_reference'] = influence_str
            lineage_data['lineage_match_score'] = round(best_score, 3)
            if used_embedding_fallback:
                lineage_data['match_method'] = 'embedding'

            bridges.append({
                'source_id': source_id,
                'target_id': target_id,
                'connection_mode': 'lineage',
                'directed': True,
                'shared_entities': json.dumps(lineage_data),
                'entity_score': round(entity_score, 4),
                'bridge_score': bridge_score,
                'text_similarity': round(text_sim, 4) if text_sim is not None else None,
                'image_similarity': round(image_sim, 4) if image_sim is not None else None,
                'year_gap': year_gap,
                'crossing_type': crossing_type,
            })

            existing_pairs.add(pair_key)
            participation[source_id] = participation.get(source_id, 0) + 1
            participation[target_id] = participation.get(target_id, 0) + 1
            matched += 1
            if used_embedding_fallback:
                matched_by_embedding += 1

    log.info(f'\n  Pass 2 complete:')
    log.info(f'    {matched} lineage bridges created ({matched_by_embedding} via embedding fallback)')
    log.info(f'    {no_match} influence references with no match')
    log.info(f'    {too_similar_count} rejected (too similar)')

    return bridges

# ---------------------------------------------------------------------------
# Pass 3: Visual Echo
# ---------------------------------------------------------------------------

def pass_3_visual_echo(product_map, idf, existing_pairs, participation, db):
    """Find bridges between products that look alike but weren't connected
    by entity matching or lineage.

    Uses pgvector image similarity search. Only considers pairs NOT already
    in existing_pairs — these are the surprises that metadata missed.
    Commits to DB in batches of 500 to survive pooler timeouts.

    Returns list of bridge dicts ready for summary (already saved to DB).
    """
    log.info('\n' + '=' * 70)
    log.info('  Pass 3: Visual Echo')
    log.info('=' * 70)

    # Only products with image embeddings
    products_with_images = [
        pid for pid, prod in product_map.items()
        if prod.get('image_emb') is not None
    ]
    log.info(f'  {len(products_with_images)} products with image embeddings')

    all_bridges = []
    batch = []
    searched = 0
    already_connected = 0
    no_boundary = 0
    too_similar_count = 0
    BATCH_SIZE = 500

    tracker = ProgressTracker(len(products_with_images), label='image queries')

    for pid in products_with_images:
        tracker.tick()
        tracker.log_every(250)

        prod = product_map[pid]
        emb = prod['image_emb']

        # Gate: participation cap
        if participation.get(pid, 0) >= MAX_BRIDGES_PER_PRODUCT:
            continue

        # pgvector kNN search for top 10 most visually similar
        emb_str = '[' + ','.join(str(x) for x in emb) + ']'
        results = db.execute(text('''
            SELECT id, 1 - (image_embedding <=> :emb) as similarity
            FROM products
            WHERE id != :pid
            AND image_embedding IS NOT NULL
            ORDER BY image_embedding <=> :emb
            LIMIT 10
        '''), {'emb': emb_str, 'pid': pid}).fetchall()

        for candidate_id, image_sim in results:
            if image_sim < VISUAL_ECHO_MIN_IMAGE_SIM:
                continue

            # Canonical pair key
            pair_key = (min(pid, candidate_id), max(pid, candidate_id))

            # Skip if already connected by Pass 1 or Pass 2
            if pair_key in existing_pairs:
                already_connected += 1
                continue

            if candidate_id not in product_map:
                continue

            candidate = product_map[candidate_id]

            # Gate: must cross a boundary
            if not _crosses_boundary(prod, candidate):
                no_boundary += 1
                continue

            # Gate: not too similar
            text_sim = _cosine_sim(prod.get('text_emb'), candidate.get('text_emb'))

            if _too_similar(prod, candidate, text_sim, image_sim):
                too_similar_count += 1
                continue

            # Gate: participation cap for candidate too
            if participation.get(candidate_id, 0) >= MAX_BRIDGES_PER_PRODUCT:
                continue

            # Score — visual echo gets entity overlap too (may share some entities)
            entity_score, shared_entities, _ = score_entity_overlap(prod, candidate, idf)
            context_score, year_gap, crossing_type = compute_context_score(prod, candidate)
            bridge_score = compute_bridge_score(entity_score, context_score, text_sim, image_sim)

            # For visual echo, add image_similarity to shared_entities for display
            visual_data = shared_entities.copy()
            visual_data['image_similarity'] = round(image_sim, 3)

            bridge_dict = {
                'source_id': pair_key[0],
                'target_id': pair_key[1],
                'connection_mode': 'visual_echo',
                'directed': False,
                'shared_entities': json.dumps(visual_data),
                'entity_score': round(entity_score, 4),
                'bridge_score': bridge_score,
                'text_similarity': round(text_sim, 4) if text_sim is not None else None,
                'image_similarity': round(image_sim, 4),
                'year_gap': year_gap,
                'crossing_type': crossing_type,
            }

            batch.append(bridge_dict)
            all_bridges.append(bridge_dict)
            existing_pairs.add(pair_key)
            participation[pid] = participation.get(pid, 0) + 1
            participation[candidate_id] = participation.get(candidate_id, 0) + 1
            searched += 1

            # Commit batch to DB
            if len(batch) >= BATCH_SIZE:
                db.bulk_insert_mappings(StyleBridge, batch)
                db.commit()
                log.info(f'    [{searched} bridges saved]')
                batch = []

    # Commit remaining
    if batch:
        db.bulk_insert_mappings(StyleBridge, batch)
        db.commit()
        log.info(f'    [{searched} bridges saved]')

    log.info(f'\n  Pass 3 complete:')
    log.info(f'    {searched} visual echo bridges created')
    log.info(f'    {already_connected} skipped (already connected by Pass 1/2)')
    log.info(f'    {no_boundary} rejected (no boundary crossing)')
    log.info(f'    {too_similar_count} rejected (too similar)')

    return all_bridges

# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------

def save_bridges(db, bridges, batch_size=500):
    """Insert bridges into the database in batches using bulk insert."""
    if not bridges:
        return 0

    log.info(f'\n  Saving {len(bridges)} bridges to database...')
    saved = 0

    for i in range(0, len(bridges), batch_size):
        batch = bridges[i:i + batch_size]
        db.bulk_insert_mappings(StyleBridge, batch)
        db.commit()
        saved += len(batch)
        log.info(f'    [{saved}/{len(bridges)}] committed')

    return saved


def _parse_embedding(emb):
    """Parse a pgvector embedding into a numpy array. Handles list, string, and pgvector types."""
    if emb is None:
        return None
    try:
        if isinstance(emb, np.ndarray):
            return emb.astype(np.float32)
        if isinstance(emb, list):
            return np.array(emb, dtype=np.float32)
        # pgvector returns as string like '[0.1,0.2,...]'
        s = str(emb).strip()
        if s.startswith('['):
            return np.array(json.loads(s), dtype=np.float32)
        # Some drivers return without brackets
        return np.array([float(x) for x in s.split(',')], dtype=np.float32)
    except (ValueError, json.JSONDecodeError) as e:
        log.warning(f'  Failed to parse embedding: {e}')
        return None


def load_embeddings(product_map, db):
    """Load text and image embeddings into product_map."""
    log.info('  Loading embeddings...')
    rows = db.execute(text(
        'SELECT id, text_embedding, image_embedding FROM products '
        'WHERE enriched_at IS NOT NULL'
    )).fetchall()

    loaded_text = 0
    loaded_image = 0
    for pid, text_emb, image_emb in rows:
        if pid not in product_map:
            continue
        if text_emb is not None:
            parsed = _parse_embedding(text_emb)
            if parsed is not None:
                product_map[pid]['text_emb'] = parsed
                loaded_text += 1
        if image_emb is not None:
            parsed = _parse_embedding(image_emb)
            if parsed is not None:
                product_map[pid]['image_emb'] = parsed
                loaded_image += 1

    log.info(f'    {loaded_text} text embeddings, {loaded_image} image embeddings')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Compute entity-based bridges')
    parser.add_argument('--rebuild', action='store_true',
                        help='Delete all existing bridges before computing')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit to N products (for testing)')
    parser.add_argument('--skip-visual', action='store_true',
                        help='Skip Pass 3 (visual echo) for faster runs')
    parser.add_argument('--dry-run', action='store_true',
                        help='Score and classify but do not write to DB')
    args = parser.parse_args()

    start_time = time.time()
    db = SessionLocal()

    try:
        # Rebuild: clear existing bridges
        if args.rebuild:
            count = db.query(StyleBridge).count()
            if count > 0:
                log.info(f'  Clearing {count} existing bridges...')
                db.query(StyleBridge).delete()
                db.commit()

        # Build product index
        product_map, inverted_index, idf = build_product_index(db)

        # Apply limit if testing
        if args.limit:
            limited_ids = set(list(product_map.keys())[:args.limit])
            product_map = {k: v for k, v in product_map.items() if k in limited_ids}
            # Filter inverted index to only include limited products
            filtered_index = defaultdict(set)
            for key, pids in inverted_index.items():
                filtered = pids & limited_ids
                if len(filtered) >= 2:
                    filtered_index[key] = filtered
            inverted_index = filtered_index
            log.info(f'  Limited to {len(product_map)} products')

        # Load embeddings for similarity gates and Pass 3
        load_embeddings(product_map, db)

        # Tracking
        existing_pairs = set()
        participation = {}

        # ---- Pass 1: Shared Entities ----
        pass_1_bridges = pass_1_shared_entities(
            product_map, inverted_index, idf, existing_pairs, participation
        )
        if not args.dry_run:
            save_bridges(db, pass_1_bridges)

        # ---- Pass 2: Lineage ----
        pass_2_bridges = pass_2_lineage(
            product_map, idf, existing_pairs, participation
        )
        if not args.dry_run:
            save_bridges(db, pass_2_bridges)

        # ---- Pass 3: Visual Echo (saves its own batches) ----
        pass_3_bridges = []
        if not args.skip_visual:
            pass_3_bridges = pass_3_visual_echo(
                product_map, idf, existing_pairs, participation, db
            )
        else:
            log.info('\n  Pass 3: Skipped (--skip-visual)')

        # ---- Summary ----
        all_bridges = pass_1_bridges + pass_2_bridges + pass_3_bridges

        if args.dry_run:
            log.info(f'\n  DRY RUN — {len(all_bridges)} bridges would be created')

        elapsed = time.time() - start_time
        log.info('\n' + '=' * 70)
        log.info('  BRIDGE COMPUTATION COMPLETE')
        log.info('=' * 70)
        log.info(f'  Total bridges: {len(all_bridges)}')
        log.info(f'  Time: {elapsed:.0f}s ({elapsed/60:.1f}m)')
        log.info('')
        log.info(f'  By pass:')
        log.info(f'    shared_entity:  {len(pass_1_bridges)}')
        log.info(f'    lineage:        {len(pass_2_bridges)}')
        log.info(f'    visual_echo:    {len(pass_3_bridges)}')

        # Crossing type breakdown
        crossing_counts = defaultdict(int)
        score_sum = 0
        for b in all_bridges:
            crossing_counts[b['crossing_type']] += 1
            score_sum += b['bridge_score']

        log.info('')
        log.info(f'  By crossing:')
        for ct, count in sorted(crossing_counts.items(), key=lambda x: -x[1]):
            log.info(f'    {ct:30s} {count:>6}')

        if all_bridges:
            avg_score = score_sum / len(all_bridges)
            scores = [b['bridge_score'] for b in all_bridges]
            log.info('')
            log.info(f'  Bridge score: avg={avg_score:.3f}  '
                     f'min={min(scores):.3f}  max={max(scores):.3f}')

        # Top shared entities
        entity_counts = defaultdict(int)
        for b in all_bridges:
            shared = json.loads(b['shared_entities'])
            for etype, values in shared.items():
                if etype in ENTITY_MULTIPLIERS and isinstance(values, list):
                    for v in values:
                        entity_counts[(etype, v)] += 1

        log.info('')
        log.info(f'  Top shared entities:')
        for (etype, value), count in sorted(entity_counts.items(), key=lambda x: -x[1])[:15]:
            log.info(f'    {count:>5}  {etype}: {value}')

    finally:
        db.close()


if __name__ == '__main__':
    main()
