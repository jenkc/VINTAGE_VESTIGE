"""
Reusable query functions for style bridge data.

Returns plain dicts (TypedDict) suitable for JSON serialization,
FastAPI responses, scripts, and tests. Every public function takes
a SQLAlchemy Session as its first argument.

Entity-based bridge system (v2). Bridges have:
  - shared_entities (JSON dict): the "why" of the connection
  - entity_score: IDF-weighted entity overlap
  - connection_mode: shared_entity | lineage | visual_echo
  - directed: True for lineage (source=older, target=newer)
  - bridge_score: precomputed composite (entity + context + embedding)
"""

from __future__ import annotations

import json
from typing import TypedDict

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from storage.database import Product, StyleBridge


# ─── Return types ─────────────────────────────────────────────────────

class ProductSummary(TypedDict):
    id: int
    platform: str
    title: str
    display_title: str | None
    primary_image: str | None
    era: str | None
    decade: str | None
    fp_category: str | None
    silhouette: str | None
    material: str | None
    culture: str | None
    style_tags: list[str]
    colors: list[str]
    ai_description: str | None
    vibe_scores: dict | None
    designer: str | None
    named_movements: list[str]
    influence_references: list[str]
    production_mode: str | None


class BridgeResult(TypedDict):
    id: int
    source: ProductSummary
    target: ProductSummary
    bridge_score: float | None
    entity_score: float | None
    text_similarity: float | None
    image_similarity: float | None
    connection_mode: str | None
    crossing_type: str | None
    year_gap: int | None
    directed: bool
    shared_entities: dict
    bridge_narrative: str | None
    created_at: str | None


class BridgeListResponse(TypedDict):
    bridges: list[BridgeResult]
    total: int
    limit: int
    offset: int


class ConnectionModeStats(TypedDict):
    connection_mode: str
    count: int
    avg_score: float


class BridgeStats(TypedDict):
    total_bridges: int
    total_products_with_bridges: int
    by_mode: list[ConnectionModeStats]
    score_histogram: list[dict]


# ─── Internal helpers ─────────────────────────────────────────────────

def _parse_json_field(value: str | None) -> list:
    """Parse a JSON text column into a list, defaulting to []."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_json_dict(value: str | None) -> dict:
    """Parse a JSON text column into a dict, defaulting to {}."""
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _product_to_summary(p: Product) -> ProductSummary:
    """Convert a SQLAlchemy Product to a plain dict."""
    vs = p.vibe_scores
    if isinstance(vs, str):
        try:
            vs = json.loads(vs)
        except (json.JSONDecodeError, TypeError):
            vs = None
    if not isinstance(vs, dict):
        vs = None

    return ProductSummary(
        id=p.id,
        platform=p.platform,
        title=p.title or '',
        display_title=p.display_title,
        primary_image=p.primary_image,
        era=p.era,
        decade=p.decade,
        fp_category=p.fp_category,
        silhouette=p.silhouette,
        material=p.material,
        culture=p.culture,
        style_tags=_parse_json_field(p.style_tags),
        colors=_parse_json_field(p.colors),
        ai_description=p.ai_description,
        vibe_scores=vs,
        designer=p.designer,
        named_movements=_parse_json_field(p.named_movements),
        influence_references=_parse_json_field(p.influence_references),
        production_mode=p.production_mode,
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
    """Assemble a BridgeResult from a bridge row and product map."""
    source = product_map.get(bridge.source_id)
    target = product_map.get(bridge.target_id)
    if not source or not target:
        return None

    return BridgeResult(
        id=bridge.id,
        source=source,
        target=target,
        bridge_score=bridge.bridge_score,
        entity_score=bridge.entity_score,
        text_similarity=bridge.text_similarity,
        image_similarity=bridge.image_similarity,
        connection_mode=bridge.connection_mode,
        crossing_type=bridge.crossing_type,
        year_gap=bridge.year_gap,
        directed=bridge.directed or False,
        shared_entities=_parse_json_dict(bridge.shared_entities),
        bridge_narrative=bridge.bridge_narrative,
        created_at=bridge.created_at.isoformat() if bridge.created_at else None,
    )


def _collect_product_ids(bridges: list[StyleBridge]) -> set[int]:
    """Collect all product IDs referenced by a list of bridges."""
    ids = set()
    for b in bridges:
        ids.add(b.source_id)
        ids.add(b.target_id)
    return ids


def _apply_filters(query, *, connection_mode=None, crossing_type=None,
                   min_score=None, max_score=None, min_year_gap=None,
                   directed=None):
    """Apply optional filters to a bridge query."""
    if connection_mode:
        query = query.filter(StyleBridge.connection_mode == connection_mode)
    if crossing_type:
        query = query.filter(StyleBridge.crossing_type == crossing_type)
    if min_score is not None:
        query = query.filter(StyleBridge.bridge_score >= min_score)
    if max_score is not None:
        query = query.filter(StyleBridge.bridge_score <= max_score)
    if min_year_gap is not None:
        query = query.filter(StyleBridge.year_gap >= min_year_gap)
    if directed is not None:
        query = query.filter(StyleBridge.directed == directed)
    return query


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
    connection_mode: str | None = None,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> BridgeListResponse:
    """Get all bridges involving a specific product, sorted by bridge_score."""
    query = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id,
        )
    )
    query = _apply_filters(query, connection_mode=connection_mode, min_score=min_score)

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


def get_top_bridges(
    db: Session,
    *,
    connection_mode: str | None = None,
    crossing_type: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    min_year_gap: int | None = None,
    directed: bool | None = None,
    sort: str = 'default',
    limit: int = 20,
    offset: int = 0,
    randomize: bool = True,
) -> BridgeListResponse:
    """Get top bridges globally, optionally filtered.

    When randomize=True (default), fetches a larger pool of top bridges
    and randomly samples from them, weighted by score. This ensures
    variety across page loads while still favoring strong bridges.
    """
    query = db.query(StyleBridge).order_by(StyleBridge.bridge_score.desc())
    query = _apply_filters(
        query, connection_mode=connection_mode, crossing_type=crossing_type,
        min_score=min_score, max_score=max_score,
        min_year_gap=min_year_gap, directed=directed,
    )

    total = query.count()

    if randomize and offset == 0:
        # Fetch a larger pool and randomly sample, weighted by score
        import random
        pool_size = min(limit * 5, total, 200)
        pool = query.limit(pool_size).all()
        if pool:
            # Weight by score — higher scores more likely to be picked
            weights = [(b.bridge_score or 0.1) ** 2 for b in pool]
            selected = random.choices(pool, weights=weights, k=min(limit, len(pool)))
            # Deduplicate (choices can repeat)
            seen = set()
            bridges = []
            for b in selected:
                if b.id not in seen:
                    seen.add(b.id)
                    bridges.append(b)
        else:
            bridges = []
    else:
        bridges = query.offset(offset).limit(limit).all()

    product_map = _batch_load_products(db, _collect_product_ids(bridges))
    return _assemble_response(bridges, product_map, total, limit, offset)


def get_bridge_detail(
    db: Session,
    bridge_id: int,
) -> BridgeResult | None:
    """Get a single bridge with full product context."""
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
    """Find the bridge between two specific products.

    Checks both orderings since lineage bridges may not use canonical ordering.
    """
    bridge = (
        db.query(StyleBridge)
        .filter(
            or_(
                (StyleBridge.source_id == product_a_id) & (StyleBridge.target_id == product_b_id),
                (StyleBridge.source_id == product_b_id) & (StyleBridge.target_id == product_a_id),
            )
        )
        .first()
    )
    if not bridge:
        return None

    product_map = _batch_load_products(db, {product_a_id, product_b_id})
    return _build_bridge_result(bridge, product_map)


def get_bridge_stats(db: Session) -> BridgeStats:
    """Aggregate bridge statistics."""
    total = db.query(func.count(StyleBridge.id)).scalar() or 0

    # Counts by connection mode
    mode_rows = (
        db.query(
            StyleBridge.connection_mode,
            func.count(StyleBridge.id),
            func.avg(StyleBridge.bridge_score),
        )
        .group_by(StyleBridge.connection_mode)
        .all()
    )
    by_mode = [
        ConnectionModeStats(
            connection_mode=row[0] or 'unknown',
            count=row[1],
            avg_score=round(float(row[2] or 0), 3),
        )
        for row in mode_rows
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

    # Score histogram using bridge_score
    histogram = []
    bucket_size = 0.1
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
        by_mode=by_mode,
        score_histogram=histogram,
    )


# ─── Temporal queries ─────────────────────────────────────────────────

def get_style_ancestry(
    db: Session,
    product_id: int,
    *,
    min_score: float | None = None,
    limit: int = 5,
    offset: int = 0,
) -> BridgeListResponse:
    """Bridges with year_gap > 30 — cross-time connections."""
    query = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id,
        ),
        StyleBridge.year_gap > 30,
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
    """Bridges with year_gap <= 30 — same-era connections."""
    query = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id == product_id,
            StyleBridge.target_id == product_id,
        ),
        or_(
            StyleBridge.year_gap <= 30,
            StyleBridge.year_gap == None,
        ),
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
