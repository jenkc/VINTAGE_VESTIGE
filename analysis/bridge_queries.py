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

from sqlalchemy import func, or_, case, cast, Integer
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
    bridge_score: float
    text_similarity: float
    image_similarity: float | None
    structural_score: float
    bridge_type: str | None
    bridge_narrative: str | None
    shared_attributes: dict
    created_at: str  # ISO 8601


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
        bridge_score=bridge.bridge_score,
        text_similarity=bridge.text_similarity,
        image_similarity=bridge.image_similarity,
        structural_score=bridge.structural_score,
        bridge_type=bridge.bridge_type,
        bridge_narrative=bridge.bridge_narrative,
        shared_attributes=shared,
        created_at=bridge.created_at.isoformat() if bridge.created_at else '',
    )


def _base_bridge_query(db: Session):
    """Start a StyleBridge query ordered by score descending."""
    return db.query(StyleBridge).order_by(StyleBridge.bridge_score.desc())


def _apply_filters(query, *, bridge_type=None, min_score=None, max_score=None):
    """Apply optional type and score filters to a bridge query."""
    if bridge_type:
        query = query.filter(StyleBridge.bridge_type == bridge_type)
    if min_score is not None:
        query = query.filter(StyleBridge.bridge_score >= min_score)
    if max_score is not None:
        query = query.filter(StyleBridge.bridge_score <= max_score)
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
        base.order_by(StyleBridge.bridge_score.desc())
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
    limit: int = 20,
    offset: int = 0,
) -> BridgeListResponse:
    """Get top bridges globally, optionally filtered.

    Platform filtering finds bridges connecting the specified platform(s).
    When both source_platform and target_platform are set, finds bridges
    that connect the two (in either direction, since canonical ordering
    is by ID not platform).
    """
    query = _base_bridge_query(db)
    query = _apply_filters(
        query, bridge_type=bridge_type, min_score=min_score, max_score=max_score
    )

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

    # Counts by type
    type_rows = (
        db.query(
            StyleBridge.bridge_type,
            func.count(StyleBridge.id),
            func.avg(StyleBridge.bridge_score),
            func.min(StyleBridge.bridge_score),
            func.max(StyleBridge.bridge_score),
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

    # Score histogram (10 buckets from 0.0 to 1.0)
    bucket_size = 0.1
    histogram = []
    for i in range(10):
        lo = round(i * bucket_size, 1)
        hi = round(lo + bucket_size, 1)
        count = (
            db.query(func.count(StyleBridge.id))
            .filter(
                StyleBridge.bridge_score >= lo,
                StyleBridge.bridge_score < hi if i < 9 else StyleBridge.bridge_score <= hi,
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
        query.order_by(StyleBridge.bridge_score.desc())
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
        query.order_by(StyleBridge.bridge_score.desc())
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

    Ordered by structural_score (Fashionpedia taxonomy overlap)
    rather than overall bridge_score.
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
