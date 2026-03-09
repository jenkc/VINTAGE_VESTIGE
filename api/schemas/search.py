"""Pydantic schemas for search endpoints."""
from __future__ import annotations
import json
from pydantic import BaseModel, field_validator, Field


class SearchFilters(BaseModel):
    """Optional filters for narrowing search results.

    Matches the frontend SearchFilters TypeScript interface in
    vv-web/src/types/index.ts.
    """

    era: str | None = None
    decade: str | None = None
    garment_type: str | None = None
    vibe: str | None = None
    occasion: str | None = None
    fit_style: str | None = None
    culture: str | None = None
    material: str | None = None


class TextSearchRequest(BaseModel):
    """Request body for POST /search/text.

    Matches the body sent by vv-web/src/lib/api.ts searchByText():
        { query, limit, filters }
    """

    query: str
    limit: int = Field(default=12, ge=1, le=100)
    filters: SearchFilters | None = None


class ImageSearchRequest(BaseModel):
    """Request body for POST /search/image.

    Field name is 'image' (base64 data URL), matching the frontend
    ImageSearchRequest TypeScript interface.
    """

    image: str
    limit: int = Field(default=12, ge=1, le=100)


class SearchResult(BaseModel):
    """A single result in a search response.

    Matches the frontend SearchResult TypeScript interface in
    vv-web/src/types/index.ts. Built from Qdrant payload + score.
    """

    id: int
    score: float
    title: str
    category: str | None = None
    primary_image: str | None = None

    # Enrichment metadata
    era: str | None = None
    decade: str | None = None
    style_tags: list[str] = []
    colors: list[str] = []
    material: str | None = None
    garment_type: str | None = None
    vibe: str | None = None
    fit_style: str | None = None
    occasion: str | None = None
    ai_description: str | None = None
    culture: str | None = None
    object_date: str | None = None
    price: float | None = None
    
    @field_validator("style_tags", "colors", mode="before")
    @classmethod
    def parse_json_lists(cls, v):
        """Handle JSON strings coming from SQL (vs lists from old Qdrant)."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v if isinstance(v, list) else []


class SearchResponse(BaseModel):
    """Response for both text and image search endpoints.

    Matches the frontend SearchResponse TypeScript interface.
    """

    results: list[SearchResult]
    query: str
    total: int
