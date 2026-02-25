"""Pydantic schemas for the Vintage Vestige API."""

from api.schemas.product import ProductSummary, ProductDetail
from api.schemas.search import (
    SearchFilters,
    TextSearchRequest,
    ImageSearchRequest,
    SearchResult,
    SearchResponse,
)
from api.schemas.bridge import (
    BridgeResult,
    BridgeListResponse,
    BridgeTypeStats,
    ScoreHistogramBucket,
    BridgeStats,
)
from api.schemas.filters import FilterOptions

__all__ = [
    "ProductSummary",
    "ProductDetail",
    "SearchFilters",
    "TextSearchRequest",
    "ImageSearchRequest",
    "SearchResult",
    "SearchResponse",
    "BridgeResult",
    "BridgeListResponse",
    "BridgeTypeStats",
    "ScoreHistogramBucket",
    "BridgeStats",
    "FilterOptions",
]
