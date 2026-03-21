"""Pydantic schemas for bridge endpoints."""

from __future__ import annotations

import json

from pydantic import BaseModel, field_validator

from api.schemas.product import ProductSummary


def _parse_json_dict(v: object) -> dict:
    """Parse a JSON-encoded TEXT column into a Python dict."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        if not v.strip():
            return {}
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


class BridgeResult(BaseModel):
    """A single style bridge with full product context.

    Entity-based bridge system (v2). Each bridge has a typed reason
    stored in shared_entities — the "why" of the connection.
    """

    id: int
    source: ProductSummary
    target: ProductSummary

    # Scores
    bridge_score: float | None = None
    entity_score: float | None = None
    text_similarity: float | None = None
    image_similarity: float | None = None

    # Classification
    connection_mode: str | None = None      # shared_entity | lineage | visual_echo
    crossing_type: str | None = None        # same_context | cross_category | cross_culture | cross_category_culture
    year_gap: int | None = None
    directed: bool = False                  # True for lineage (source=older, target=newer)

    # Entity data — the "why" of the connection
    shared_entities: dict = {}              # {entity_type: [values], lineage_reference?: str}

    # Narrative
    bridge_narrative: str | None = None

    created_at: str | None = None           # ISO 8601

    @field_validator("shared_entities", mode="before")
    @classmethod
    def parse_shared_entities(cls, v: object) -> dict:
        return _parse_json_dict(v)


class BridgeListResponse(BaseModel):
    """Paginated list of bridges."""

    bridges: list[BridgeResult]
    total: int
    limit: int
    offset: int


class ConnectionModeStats(BaseModel):
    """Statistics for a single connection mode."""

    connection_mode: str
    count: int
    avg_score: float


class ScoreHistogramBucket(BaseModel):
    """A single bucket in the score histogram."""

    bucket: str
    count: int


class BridgeStats(BaseModel):
    """Aggregate bridge statistics."""

    total_bridges: int
    total_products_with_bridges: int
    by_mode: list[ConnectionModeStats]
    score_histogram: list[ScoreHistogramBucket]
