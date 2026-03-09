"""Pydantic schemas for bridge endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from api.schemas.product import ProductSummary


class BridgeResult(BaseModel):
    """A single style bridge with full product context.

    Mirrors the BridgeResult TypedDict in analysis/bridge_queries.py.
    Used by GET /bridges/{id}, GET /bridges/between/{a}/{b},
    and as items in BridgeListResponse.
    """

    id: int
    source: ProductSummary
    target: ProductSummary
    bridge_score: float
    text_similarity: float
    image_similarity: float | None = None
    structural_score: float
    bridge_type: str | None = None
    bridge_narrative: str | None = None
    shared_attributes: dict = {}
    created_at: str  # ISO 8601
    temporal_type: str | None = None
    crossing_type: str | None = None
    connection_mode: str | None = None
    primary_axis: str | None = None
    secondary_axis: str | None = None
    contrast_pair: str | None = None

class BridgeListResponse(BaseModel):
    """Paginated list of bridges.

    Mirrors the BridgeListResponse TypedDict in
    analysis/bridge_queries.py.
    """

    bridges: list[BridgeResult]
    total: int
    limit: int
    offset: int


class BridgeTypeStats(BaseModel):
    """Statistics for a single bridge type."""

    bridge_type: str
    count: int
    avg_score: float
    min_score: float
    max_score: float


class ScoreHistogramBucket(BaseModel):
    """A single bucket in the score histogram."""

    bucket: str
    count: int


class BridgeStats(BaseModel):
    """Aggregate bridge statistics.

    Mirrors the BridgeStats TypedDict in analysis/bridge_queries.py.
    Used by GET /bridges/stats.
    """

    total_bridges: int
    total_products_with_bridges: int
    by_type: list[BridgeTypeStats]
    score_histogram: list[ScoreHistogramBucket]
