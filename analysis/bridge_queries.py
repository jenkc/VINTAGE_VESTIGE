"""
Reusable query functions for style bridge data.

Returns plain dicts (TypedDict) suitable for JSON serialization,
FastAPI responses, scripts, and tests. Every public function takes
a SQLAlchemy Session as its first argument.

Usage from scripts:
    from storage.database import SessionLocal
    from analysis.bridge_queries import get_bridges_for_product
    db = SessionLocal()
    result = get_bridges_for_product(db, product_id=42)
    db.close()

Usage from FastAPI:
    @app.get("/bridges/{product_id}")
    def bridges(product_id: int, db: Session = Depends(get_db)):
        return get_bridges_for_product(db, product_id)
"""

from __future__ import annotations

import json
from typing import TypedDict

from sqlalchemy import func, or_, case, cast, Integer, text, literal_column
from sqlalchemy.orm import Session, aliased

from storage.database import Product, StyleBridge


# ─── Return types ─────────────────────────────────────────────────────

class ProductSummary(TypedDict):
    id: int
    platform: str
    title: str
    primary_image: str | None
    era: str | None
    decade: str | None
    fp_category: str | None
    silhouette: str | None
    vibe: str | None
    material: str | None
    style_tags: list[str]
    colors: list[str]
    ai_description: str | None


class BridgeResult(TypedDict):
    id: int
    source: ProductSummary
    target: ProductSummary
    bridge_score: float  # computed at query time from component scores + connection_mode
    text_similarity: float
    image_similarity: float | None
    structural_score: float
    bridge_type: str | None
    bridge_narrative: str | None
    shared_attributes: dict
    created_at: str  # ISO 8601
    temporal_type: str | None
    crossing_type: str | None
    connection_mode: str | None
    primary_axis: str | None
    secondary_axis: str | None
    contrast_pair: str | None


class BridgeListResponse(TypedDict):
    bridges: list[BridgeResult]
    total: int
    limit: int
    offset: int


class BridgeTypeStats(TypedDict):
    bridge_type: str
    count: int
    avg_score: float
    min_score: float
    max_score: float


class BridgeStats(TypedDict):
    total_bridges: int
    total_products_with_bridges: int
    by_type: list[BridgeTypeStats]
    score_histogram: list[dict]


# ─── Mode-aware scoring ──────────────────────────────────────────────
#
# Instead of a single stored bridge_score with fixed weights, we compute
# a composite on the fly. Different connection modes emphasize different
# component scores:
#   contrast  → structural matters most (they share enough form to argue)
#   resonance → text matters most (same aesthetic language across time)
#   affinity  → balanced across all three
#   (default) → balanced (used when connection_mode is NULL)

MODE_WEIGHTS: dict[str | None, tuple[float, float, float]] = {
    # (text_weight, image_weight, structural_weight)
    'contrast':  (0.20, 0.20, 0.60),
    'resonance': (0.60, 0.20, 0.20),
    'affinity':  (0.40, 0.30, 0.30),
    None:        (0.40, 0.30, 0.30),  # default / unclassified
}


def compute_bridge_score(
    text_sim: float,
    image_sim: float | None,
    structural: float,
    connection_mode: str | None = None,
) -> float:
    """Compute a mode-aware composite bridge score from component scores."""
    tw, iw, sw = MODE_WEIGHTS.get(connection_mode, MODE_WEIGHTS[None])
    if image_sim is not None:
        return round(tw * text_sim + iw * image_sim + sw * structural, 4)
    else:
        # Redistribute image weight proportionally
        total = tw + sw
        return round((tw / total) * text_sim + (sw / total) * structural, 4)


# SQL expression for mode-aware composite (used in ORDER BY / WHERE)
# Uses CASE on connection_mode to pick weights at the database level.
_COMPOSITE_EXPR = ("(CASE"
    " WHEN connection_mode = 'contrast' AND image_similarity IS NOT NULL"
    "   THEN 0.20 * text_similarity + 0.20 * image_similarity + 0.60 * structural_score"
    " WHEN connection_mode = 'contrast'"
    "   THEN (0.20/0.80) * text_similarity + (0.60/0.80) * structural_score"
    " WHEN connection_mode = 'resonance' AND image_similarity IS NOT NULL"
    "   THEN 0.60 * text_similarity + 0.20 * image_similarity + 0.20 * structural_score"
    " WHEN connection_mode = 'resonance'"
    "   THEN (0.60/0.80) * text_similarity + (0.20/0.80) * structural_score"
    " WHEN image_similarity IS NOT NULL"
    "   THEN 0.40 * text_similarity + 0.30 * image_similarity + 0.30 * structural_score"
    " ELSE (0.40/0.70) * text_similarity + (0.30/0.70) * structural_score"
    " END)")
_COMPOSITE_SQL = literal_column(_COMPOSITE_EXPR)
_COMPOSITE_DESC = text(f"{_COMPOSITE_EXPR} DESC")


# ─── Internal helpers ─────────────────────────────────────────────────

def _parse_json_field(value: str | None) -> list:
    """Parse a JSON text column into a list, defaulting to []."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _product_to_summary(p: Product) -> ProductSummary:
    """Convert a SQLAlchemy Product to a plain dict."""
    return ProductSummary(
        id=p.id,
        platform=p.platform,
        title=p.title or '',
        primary_image=p.primary_image,
        era=p.era,
        decade=p.decade,
        fp_category=p.fp_category,
        silhouette=p.silhouette,
        vibe=p.vibe,
        material=p.material,
        style_tags=_parse_json_field(p.style_tags),
        colors=_parse_json_field(p.colors),
        ai_description=p.ai_description,
    )


def _batch_load_products(
    db: Session, product_ids: set[int]
) -> dict[int, ProductSummary]:
    """Load products by ID in a single query. Returns {id: ProductSummary}."""
    if not product_ids:
        return {}
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    return {p.id: _product_to_summary(p) for p in products}


def _build_bridge_result(
    bridge: StyleBridge, product_map: dict[int, ProductSummary]
) -> BridgeResult | None:
    """Assemble a BridgeResult from a bridge row and product map.
    Returns None if either product is missing."""
    source = product_map.get(bridge.source_id)
    target = product_map.get(bridge.target_id)
    if not source or not target:
        return None

    try:
        shared = json.loads(bridge.shared_attributes) if bridge.shared_attributes else {}
    except (json.JSONDecodeError, TypeError):
        shared = {}

    return BridgeResult(
        id=bridge.id,
        source=source,
        target=target,
        bridge_score=compute_bridge_score(
            bridge.text_similarity,
            bridge.image_similarity,
            bridge.structural_score,
            bridge.connection_mode,
        ),
        text_similarity=bridge.text_similarity,
        image_similarity=bridge.image_similarity,
        structural_score=bridge.structural_score,
        bridge_type=bridge.bridge_type,
        bridge_narrative=bridge.bridge_narrative,
        shared_attributes=shared,
        created_at=bridge.created_at.isoformat() if bridge.created_at else '',
        temporal_type=bridge.temporal_type,
        crossing_type=bridge.crossing_type,
        connection_mode=bridge.connection_mode,
        primary_axis=bridge.primary_axis,
        secondary_axis=bridge.secondary_axis,
        contrast_pair=bridge.contrast_pair,

    )


# Sort strategies: each maps to a SQL ORDER BY expression.
# 'default' uses the mode-aware composite (contrast bridges rank by structural,
# resonance by text, etc.). Other strategies override with a fixed formula.
SORT_STRATEGIES = {
    'default':    text(f"{_COMPOSITE_EXPR} DESC"),
    'text':       StyleBridge.text_similarity.desc(),
    'structural': StyleBridge.structural_score.desc(),
    'contrast':   text("(0.60 * structural_score + 0.20 * text_similarity + 0.20 * COALESCE(image_similarity, 0)) DESC"),
    'discovery':  text("(structural_score - text_similarity) DESC"),
    'resonance':  text("(0.60 * text_similarity + 0.20 * COALESCE(image_similarity, 0) + 0.20 * structural_score) DESC"),
}

VALID_SORTS = set(SORT_STRATEGIES.keys())


def _base_bridge_query(db: Session, sort: str = 'default'):
    """Start a StyleBridge query with configurable sort strategy."""
    order = SORT_STRATEGIES.get(sort, SORT_STRATEGIES['default'])
    return db.query(StyleBridge).order_by(order)


def _apply_filters(query, *, bridge_type=None, min_score=None, max_score=None,
                   temporal_type=None, crossing_type=None, connection_mode=None,
                   primary_axis=None,
                   shared_function=None):
    """Apply optional type and score filters to a bridge query."""
    if bridge_type:
        query = query.filter(StyleBridge.bridge_type == bridge_type)
    if min_score is not None:
        query = query.filter(_COMPOSITE_SQL >= min_score)
    if max_score is not None:
        query = query.filter(_COMPOSITE_SQL <= max_score)
    if temporal_type:
        query = query.filter(StyleBridge.temporal_type == temporal_type)
    if crossing_type:
        query = query.filter(StyleBridge.crossing_type == crossing_type)
    if connection_mode:
        query = query.filter(StyleBridge.connection_mode == connection_mode)
    if primary_axis:
        query = query.filter(StyleBridge.primary_axis == primary_axis)
    if shared_function:
        query = query.filter(
            text("shared_attributes::jsonb -> 'social_function' @> :fn_json").bindparams(fn_json=json.dumps([shared_function]))
        )

    return query


def _collect_product_ids(bridges: list[StyleBridge]) -> set[int]:
    """Collect all product IDs referenced by a list of bridges."""
    ids = set()
    for b in bridges:
        ids.add(b.source_id)
        ids.add(b.target_id)
    return ids


def _assemble_response(
    bridges: list[StyleBridge],
    product_map: dict[int, ProductSummary],
    total: int,
    limit: int,
    offset: int,
) -> BridgeListResponse:
    """Build a paginated response from bridge rows and product map."""
    results = []
    for b in bridges:
        result = _build_bridge_result(b, product_map)
        if result:
            results.append(result)
    return BridgeListResponse(
        bridges=results, total=total, limit=limit, offset=offset
    )


# ─── Public API ───────────────────────────────────────────────────────

def get_bridges_for_product(
    db: Session,
    product_id: int,
    *,
    bridge_type: str | None = None,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> BridgeListResponse:
    """Get all bridges involving a specific product.

    Handles canonical ordering transparently — checks both
    source_id and target_id columns.
    """
    base = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id,
        )
    )
    base = _apply_filters(base, bridge_type=bridge_type, min_score=min_score)

    total = base.count()
    bridges = (
        base.order_by(_COMPOSITE_DESC)
        .offset(offset)
        .limit(limit)
        .all()
    )

    product_ids = _collect_product_ids(bridges)
    product_ids.add(product_id)
    product_map = _batch_load_products(db, product_ids)

    return _assemble_response(bridges, product_map, total, limit, offset)


def get_top_bridges(
    db: Session,
    *,
    bridge_type: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    source_platform: str | None = None,
    target_platform: str | None = None,
    temporal_type: str | None = None,
    crossing_type: str | None = None,
    connection_mode: str | None = None,
    primary_axis: str | None = None,
    shared_function: str | None = None,
    sort: str = 'default',
    limit: int = 20,
    offset: int = 0,
) -> BridgeListResponse:
    """Get top bridges globally, optionally filtered.

    Platform filtering finds bridges connecting the specified platform(s).
    When both source_platform and target_platform are set, finds bridges
    that connect the two (in either direction, since canonical ordering
    is by ID not platform).
    """
    query = _base_bridge_query(db, sort=sort)
    query = _apply_filters(query, bridge_type=bridge_type, min_score=min_score, max_score=max_score,  temporal_type=temporal_type, crossing_type=crossing_type, connection_mode=connection_mode, primary_axis=primary_axis, shared_function=shared_function)


    # Platform filtering requires joining Product
    if source_platform or target_platform:
        SrcProduct = aliased(Product)
        TgtProduct = aliased(Product)
        query = (
            query
            .join(SrcProduct, StyleBridge.source_id == SrcProduct.id)
            .join(TgtProduct, StyleBridge.target_id == TgtProduct.id)
        )
        if source_platform and target_platform:
            # Check both directions (canonical order is by ID, not platform)
            query = query.filter(
                or_(
                    (SrcProduct.platform == source_platform)
                    & (TgtProduct.platform == target_platform),
                    (SrcProduct.platform == target_platform)
                    & (TgtProduct.platform == source_platform),
                )
            )
        else:
            platform = source_platform or target_platform
            query = query.filter(
                or_(
                    SrcProduct.platform == platform,
                    TgtProduct.platform == platform,
                )
            )

    total = query.count()
    bridges = query.offset(offset).limit(limit).all()

    product_map = _batch_load_products(db, _collect_product_ids(bridges))
    return _assemble_response(bridges, product_map, total, limit, offset)


def get_bridge_detail(
    db: Session,
    bridge_id: int,
) -> BridgeResult | None:
    """Get a single bridge with full product context.
    Returns None if bridge not found."""
    bridge = db.query(StyleBridge).filter(StyleBridge.id == bridge_id).first()
    if not bridge:
        return None

    product_map = _batch_load_products(
        db, {bridge.source_id, bridge.target_id}
    )
    return _build_bridge_result(bridge, product_map)


def get_bridge_between(
    db: Session,
    product_a_id: int,
    product_b_id: int,
) -> BridgeResult | None:
    """Find the bridge between two specific products, if one exists.

    Handles canonical ordering: normalizes with min/max to match
    the UniqueConstraint on (source_id, target_id).
    """
    lo, hi = min(product_a_id, product_b_id), max(product_a_id, product_b_id)
    bridge = (
        db.query(StyleBridge)
        .filter(StyleBridge.source_id == lo, StyleBridge.target_id == hi)
        .first()
    )
    if not bridge:
        return None

    product_map = _batch_load_products(db, {lo, hi})
    return _build_bridge_result(bridge, product_map)


def get_bridge_stats(db: Session) -> BridgeStats:
    """Aggregate bridge statistics: counts by type, score distribution,
    total connected products."""
    total = db.query(func.count(StyleBridge.id)).scalar() or 0

    # Counts by type (use text_similarity as representative score for stats)
    type_rows = (
        db.query(
            StyleBridge.bridge_type,
            func.count(StyleBridge.id),
            func.avg(StyleBridge.text_similarity),
            func.min(StyleBridge.text_similarity),
            func.max(StyleBridge.text_similarity),
        )
        .group_by(StyleBridge.bridge_type)
        .all()
    )
    by_type = [
        BridgeTypeStats(
            bridge_type=row[0] or 'unknown',
            count=row[1],
            avg_score=round(float(row[2]), 3),
            min_score=round(float(row[3]), 3),
            max_score=round(float(row[4]), 3),
        )
        for row in type_rows
    ]

    # Total distinct products with at least one bridge
    product_count = (
        db.query(func.count())
        .select_from(
            db.query(StyleBridge.source_id)
            .distinct()
            .union(db.query(StyleBridge.target_id).distinct())
            .subquery()
        )
        .scalar()
    ) or 0

    # Score histogram (10 buckets from 0.0 to 1.0, using text_similarity)
    bucket_size = 0.1
    histogram = []
    for i in range(10):
        lo = round(i * bucket_size, 1)
        hi = round(lo + bucket_size, 1)
        count = (
            db.query(func.count(StyleBridge.id))
            .filter(
                StyleBridge.text_similarity >= lo,
                StyleBridge.text_similarity < hi if i < 9 else StyleBridge.text_similarity <= hi,
            )
            .scalar()
        ) or 0
        histogram.append({
            'bucket': f'{lo:.1f}-{hi:.1f}',
            'count': count,
        })

    return BridgeStats(
        total_bridges=total,
        total_products_with_bridges=product_count,
        by_type=by_type,
        score_histogram=histogram,
    )


# ─── Temporal & structural queries ───────────────────────────────────

_YEAR_CUTOFF = 2000


def _other_product_id(product_id: int):
    """SQL CASE that resolves to the *other* product in a bridge."""
    return case(
        (StyleBridge.source_id == product_id, StyleBridge.target_id),
        else_=StyleBridge.source_id,
    )


def _other_year_expr(other_product):
    """SQL expression: extract leading 4-digit year from decade string."""
    return cast(func.substring(other_product.decade, '([0-9]{4})'), Integer)


def get_modern_echoes(
    db: Session,
    product_id: int,
    *,
    min_score: float | None = None,
    limit: int = 5,
    offset: int = 0,
) -> BridgeListResponse:
    """For a pre-2000 item, find its post-2000 counterparts.

    Joins to the 'other' product in each bridge and filters where
    that product's decade is year 2000 or later.
    """
    OtherProduct = aliased(Product)
    query = (
        db.query(StyleBridge)
        .join(OtherProduct, _other_product_id(product_id) == OtherProduct.id)
        .filter(
            or_(
                StyleBridge.source_id == product_id,
                StyleBridge.target_id == product_id,
            )
        )
        .filter(_other_year_expr(OtherProduct) >= _YEAR_CUTOFF)
    )
    query = _apply_filters(query, min_score=min_score)

    total = query.count()
    bridges = (
        query.order_by(_COMPOSITE_DESC)
        .offset(offset)
        .limit(limit)
        .all()
    )

    product_ids = _collect_product_ids(bridges)
    product_ids.add(product_id)
    product_map = _batch_load_products(db, product_ids)

    return _assemble_response(bridges, product_map, total, limit, offset)


def get_style_ancestry(
    db: Session,
    product_id: int,
    *,
    min_score: float | None = None,
    limit: int = 5,
    offset: int = 0,
) -> BridgeListResponse:
    """For a post-2000 item, find its pre-2000 ancestors.

    Joins to the 'other' product in each bridge and filters where
    that product's decade is before year 2000.
    """
    OtherProduct = aliased(Product)
    query = (
        db.query(StyleBridge)
        .join(OtherProduct, _other_product_id(product_id) == OtherProduct.id)
        .filter(
            or_(
                StyleBridge.source_id == product_id,
                StyleBridge.target_id == product_id,
            )
        )
        .filter(_other_year_expr(OtherProduct) < _YEAR_CUTOFF)
    )
    query = _apply_filters(query, min_score=min_score)

    total = query.count()
    bridges = (
        query.order_by(_COMPOSITE_DESC)
        .offset(offset)
        .limit(limit)
        .all()
    )

    product_ids = _collect_product_ids(bridges)
    product_ids.add(product_id)
    product_map = _batch_load_products(db, product_ids)

    return _assemble_response(bridges, product_map, total, limit, offset)


def get_style_siblings(
    db: Session,
    product_id: int,
    *,
    min_score: float | None = None,
    limit: int = 10,
    offset: int = 0,
) -> BridgeListResponse:
    """Items with the most shared structural attributes, regardless of era.

    Ordered by structural_score (Fashionpedia taxonomy overlap).
    """
    query = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id,
        )
    )
    query = _apply_filters(query, min_score=min_score)

    total = query.count()
    bridges = (
        query.order_by(StyleBridge.structural_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    product_ids = _collect_product_ids(bridges)
    product_ids.add(product_id)
    product_map = _batch_load_products(db, product_ids)

    return _assemble_response(bridges, product_map, total, limit, offset)
