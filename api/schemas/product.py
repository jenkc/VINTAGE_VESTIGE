"""Pydantic schemas for product endpoints."""

from __future__ import annotations

import json

from pydantic import BaseModel, field_validator


def _parse_json_list(v: object) -> list[str]:
    """Parse a JSON-encoded TEXT column into a Python list.

    Handles: None -> [], "" -> [], valid JSON string -> list,
    already-a-list -> pass through, anything else -> [].
    Mirrors analysis/bridge_queries._parse_json_field().
    """
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        if not v.strip():
            return []
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


class ProductSummary(BaseModel):
    """Compact product representation used inside bridge results.

    Matches the ProductSummary TypedDict in analysis/bridge_queries.py.
    """

    model_config = {"from_attributes": True}

    id: int
    platform: str
    title: str
    primary_image: str | None = None
    era: str | None = None
    decade: str | None = None
    fp_category: str | None = None
    silhouette: str | None = None
    vibe: str | None = None
    material: str | None = None
    style_tags: list[str] = []
    colors: list[str] = []
    ai_description: str | None = None

    @field_validator("style_tags", "colors", mode="before")
    @classmethod
    def parse_json_lists(cls, v: object) -> list[str]:
        return _parse_json_list(v)


class ProductDetail(BaseModel):
    """Full product detail returned by GET /products/{id}.

    Matches the frontend Product TypeScript interface in
    vv-web/src/types/index.ts, plus Fashionpedia taxonomy fields.
    """

    model_config = {"from_attributes": True}

    id: int
    external_id: str
    platform: str

    # Basic info
    title: str
    description: str | None = None
    category: str | None = None
    price: float | None = None
    currency: str = "USD"

    # Images
    primary_image: str | None = None
    image_urls: list[str] | None = None

    # Source metadata
    culture: str | None = None
    object_date: str | None = None

    # Enrichment fields
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

    # Fashionpedia taxonomy
    fp_category: str | None = None
    silhouette: str | None = None
    neckline: str | None = None
    waistline: str | None = None
    length: str | None = None
    sleeve_length: str | None = None
    opening_type: str | None = None
    textile_pattern: str | None = None
    textile_finishing: list[str] = []
    nickname: str | None = None
    garment_parts: list[str] = []
    decorations: list[str] = []

    @field_validator(
        "style_tags", "colors", "textile_finishing",
        "garment_parts", "decorations",
        mode="before",
    )
    @classmethod
    def parse_json_lists(cls, v: object) -> list[str]:
        return _parse_json_list(v)

    @field_validator("image_urls", mode="before")
    @classmethod
    def parse_nullable_json_list(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        return _parse_json_list(v)
